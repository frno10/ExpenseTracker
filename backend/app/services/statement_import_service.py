"""
Statement import service for handling file uploads and processing.
"""
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import and_, or_

from ..models.expense import ExpenseCreate, ExpenseTable
from ..parsers.base import ParseResult, ParsedTransaction
from ..parsers.registry import parser_registry
from ..repositories.expense import ExpenseRepository
from ..repositories.merchant import MerchantRepository
from .file_security_service import FileSecurityService

logger = logging.getLogger(__name__)


class UploadRecord(BaseModel):
    """Upload record model."""
    upload_id: str
    user_id: str
    filename: str
    file_size: int
    file_path: Optional[str]
    file_hash: Optional[str]
    detected_parser: Optional[str]
    bank_hint: Optional[str]
    validation_errors: List[str]
    created_at: datetime
    status: str  # 'uploaded', 'parsed', 'imported', 'failed'


class ImportResult(BaseModel):
    """Import execution result."""
    import_id: str
    success: bool
    imported_count: int
    skipped_count: int
    duplicate_count: int
    errors: List[str]
    rollback_token: Optional[str] = None  # Token for rollback capability


class DuplicateMatch(BaseModel):
    """Duplicate transaction match."""
    transaction_index: int
    existing_expense_id: str
    match_score: float
    match_reasons: List[str]


class TransactionMatch(BaseModel):
    """Transaction matching result."""
    transaction: ParsedTransaction
    duplicates: List[DuplicateMatch]
    is_likely_duplicate: bool
    confidence_score: float


class StatementImportService:
    """Service for handling statement import workflow."""
    
    def __init__(self):
        self.expense_repo = ExpenseRepository()
        self.merchant_repo = MerchantRepository()
        self.file_security = FileSecurityService()
        self._upload_records: Dict[str, UploadRecord] = {}
        self._parse_results: Dict[str, ParseResult] = {}
        self._import_rollback_data: Dict[str, List[str]] = {}  # import_id -> expense_ids
    
    async def create_upload_record(
        self,
        user_id: str,
        filename: str,
        file_size: int,
        file_path: Optional[str],
        detected_parser: Optional[str],
        bank_hint: Optional[str],
        validation_errors: List[str]
    ) -> str:
        """
        Create a new upload record with enhanced security validation.
        
        Args:
            user_id: ID of the user uploading the file
            filename: Original filename
            file_size: Size of the file in bytes
            file_path: Path to the temporary file
            detected_parser: Name of the detected parser
            bank_hint: Optional bank hint from user
            validation_errors: List of validation errors
            
        Returns:
            Upload ID
        """
        upload_id = str(uuid4())
        
        # Enhanced file validation with security checks
        if file_path and os.path.exists(file_path):
            is_valid, security_errors = await self.file_security.validate_file(
                file_path, filename
            )
            validation_errors.extend(security_errors)
        
        # Calculate file hash if file exists
        file_hash = None
        if file_path and os.path.exists(file_path):
            file_hash = self.file_security.calculate_file_hash(file_path)
        
        record = UploadRecord(
            upload_id=upload_id,
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            file_path=file_path,
            file_hash=file_hash,
            detected_parser=detected_parser,
            bank_hint=bank_hint,
            validation_errors=validation_errors,
            created_at=datetime.utcnow(),
            status='uploaded' if not validation_errors else 'failed'
        )
        
        self._upload_records[upload_id] = record
        logger.info(f"Created upload record: {upload_id}")
        
        return upload_id
    
    async def get_upload_record(self, upload_id: str, user_id: str) -> Optional[UploadRecord]:
        """
        Get an upload record by ID and user ID.
        
        Args:
            upload_id: Upload ID
            user_id: User ID (for security)
            
        Returns:
            Upload record or None if not found
        """
        record = self._upload_records.get(upload_id)
        if record and record.user_id == user_id:
            return record
        return None
    
    async def parse_statement_file(self, upload_record: UploadRecord) -> ParseResult:
        """
        Parse a statement file using the appropriate parser.
        
        Args:
            upload_record: Upload record containing file information
            
        Returns:
            Parse result
        """
        if not upload_record.file_path or not os.path.exists(upload_record.file_path):
            return ParseResult(
                success=False,
                errors=["File not found or has been deleted"]
            )
        
        # Get the appropriate parser
        parser = None
        if upload_record.detected_parser:
            parser = parser_registry.get_parser(upload_record.detected_parser)
        
        if not parser:
            parser = parser_registry.find_parser(upload_record.file_path)
        
        if not parser:
            return ParseResult(
                success=False,
                errors=["No suitable parser found for this file"]
            )
        
        try:
            # Parse the file
            logger.info(f"Parsing file with {parser.config.name}: {upload_record.filename}")
            parse_result = await parser.parse(upload_record.file_path)
            
            # Update upload record status
            upload_record.status = 'parsed' if parse_result.success else 'failed'
            
            return parse_result
            
        except Exception as e:
            logger.error(f"Error parsing file {upload_record.filename}: {e}")
            upload_record.status = 'failed'
            return ParseResult(
                success=False,
                errors=[f"Parsing failed: {str(e)}"]
            )
    
    async def store_parse_result(self, upload_id: str, parse_result: ParseResult):
        """
        Store parse result for later import.
        
        Args:
            upload_id: Upload ID
            parse_result: Parse result to store
        """
        self._parse_results[upload_id] = parse_result
        logger.info(f"Stored parse result for {upload_id}: {len(parse_result.transactions)} transactions")
    
    async def execute_import(
        self,
        upload_id: str,
        user_id: str,
        selected_transactions: Optional[List[int]] = None,
        category_mappings: Optional[Dict[str, str]] = None,
        merchant_mappings: Optional[Dict[str, str]] = None
    ) -> ImportResult:
        """
        Execute the import of parsed transactions with rollback capability.
        
        Args:
            upload_id: Upload ID
            user_id: User ID
            selected_transactions: Indices of transactions to import (None = all)
            category_mappings: Custom category mappings
            merchant_mappings: Custom merchant mappings
            
        Returns:
            Import result with rollback token
        """
        import_id = str(uuid4())
        rollback_token = str(uuid4())
        imported_expense_ids = []
        
        try:
            # Get upload record and parse result
            upload_record = await self.get_upload_record(upload_id, user_id)
            if not upload_record:
                return ImportResult(
                    import_id=import_id,
                    success=False,
                    imported_count=0,
                    skipped_count=0,
                    duplicate_count=0,
                    errors=["Upload record not found"]
                )
            
            parse_result = self._parse_results.get(upload_id)
            if not parse_result:
                return ImportResult(
                    import_id=import_id,
                    success=False,
                    imported_count=0,
                    skipped_count=0,
                    duplicate_count=0,
                    errors=["Parse result not found. Please preview the file first."]
                )
            
            # Determine which transactions to import
            transactions_to_import = parse_result.transactions
            if selected_transactions is not None:
                transactions_to_import = [
                    parse_result.transactions[i] 
                    for i in selected_transactions 
                    if 0 <= i < len(parse_result.transactions)
                ]
            
            # Analyze for duplicates before importing
            transaction_matches = await self.analyze_transaction_matches(
                transactions_to_import, user_id
            )
            
            # Import transactions
            imported_count = 0
            skipped_count = 0
            duplicate_count = 0
            errors = []
            
            for i, transaction in enumerate(transactions_to_import):
                try:
                    # Check if this transaction was flagged as likely duplicate
                    match = transaction_matches[i] if i < len(transaction_matches) else None
                    if match and match.is_likely_duplicate:
                        duplicate_count += 1
                        logger.info(f"Skipping likely duplicate: {transaction.description}")
                        continue
                    
                    # Apply custom mappings
                    processed_transaction = await self._process_transaction(
                        transaction, 
                        category_mappings or {}, 
                        merchant_mappings or {},
                        user_id
                    )
                    
                    # Create expense
                    expense_data = ExpenseCreate(
                        amount=processed_transaction.amount,
                        description=processed_transaction.description,
                        date=processed_transaction.date,
                        category_id=None,  # Will be resolved by category name
                        merchant_id=None,  # Will be resolved by merchant name
                        payment_method_id=None,  # Could be enhanced later
                        notes=processed_transaction.notes,
                        tags=[]
                    )
                    
                    # Create the expense
                    expense = await self.expense_repo.create(expense_data, user_id)
                    if expense:
                        imported_count += 1
                        imported_expense_ids.append(str(expense.id))
                        logger.debug(f"Imported expense: {expense.id}")
                    else:
                        skipped_count += 1
                        errors.append(f"Failed to create expense for: {transaction.description}")
                        
                except Exception as e:
                    logger.error(f"Error importing transaction: {e}")
                    skipped_count += 1
                    errors.append(f"Error importing transaction: {str(e)}")
            
            # Store rollback data
            if imported_expense_ids:
                self._import_rollback_data[rollback_token] = imported_expense_ids
            
            # Update upload record status
            upload_record.status = 'imported'
            
            # Clean up temporary file
            if upload_record.file_path and os.path.exists(upload_record.file_path):
                try:
                    os.unlink(upload_record.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")
            
            return ImportResult(
                import_id=import_id,
                success=True,
                imported_count=imported_count,
                skipped_count=skipped_count,
                duplicate_count=duplicate_count,
                errors=errors,
                rollback_token=rollback_token if imported_expense_ids else None
            )
            
        except Exception as e:
            logger.error(f"Error during import execution: {e}")
            
            # Attempt to rollback any expenses that were created
            if imported_expense_ids:
                try:
                    await self._rollback_expenses(imported_expense_ids, user_id)
                    logger.info(f"Rolled back {len(imported_expense_ids)} expenses due to error")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback expenses: {rollback_error}")
            
            return ImportResult(
                import_id=import_id,
                success=False,
                imported_count=0,
                skipped_count=0,
                duplicate_count=0,
                errors=[f"Import failed: {str(e)}"]
            )
    
    async def get_import_history(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict]:
        """
        Get import history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            List of import history records
        """
        # Filter records for the user
        user_records = [
            record for record in self._upload_records.values()
            if record.user_id == user_id
        ]
        
        # Sort by creation date (newest first)
        user_records.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        paginated_records = user_records[offset:offset + limit]
        
        # Convert to dict format
        history = []
        for record in paginated_records:
            history.append({
                "upload_id": record.upload_id,
                "filename": record.filename,
                "file_size": record.file_size,
                "detected_parser": record.detected_parser,
                "bank_hint": record.bank_hint,
                "status": record.status,
                "created_at": record.created_at.isoformat(),
                "has_errors": bool(record.validation_errors)
            })
        
        return history
    
    async def delete_upload(self, upload_id: str, user_id: str) -> bool:
        """
        Delete an upload and its associated data.
        
        Args:
            upload_id: Upload ID
            user_id: User ID (for security)
            
        Returns:
            True if deleted, False if not found
        """
        record = await self.get_upload_record(upload_id, user_id)
        if not record:
            return False
        
        # Delete temporary file
        if record.file_path and os.path.exists(record.file_path):
            try:
                os.unlink(record.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
        
        # Remove from memory
        self._upload_records.pop(upload_id, None)
        self._parse_results.pop(upload_id, None)
        
        logger.info(f"Deleted upload: {upload_id}")
        return True
    
    async def analyze_transaction_matches(
        self, 
        transactions: List[ParsedTransaction], 
        user_id: str
    ) -> List[TransactionMatch]:
        """
        Analyze transactions for potential duplicates.
        
        Args:
            transactions: List of parsed transactions
            user_id: User ID
            
        Returns:
            List of transaction matches with duplicate analysis
        """
        matches = []
        
        for i, transaction in enumerate(transactions):
            duplicates = await self._find_duplicate_transactions(transaction, user_id)
            
            # Calculate confidence score
            confidence_score = 1.0
            is_likely_duplicate = False
            
            if duplicates:
                # Reduce confidence based on number and quality of matches
                best_match_score = max(dup.match_score for dup in duplicates)
                confidence_score = 1.0 - (best_match_score * 0.8)
                is_likely_duplicate = best_match_score > 0.8
            
            matches.append(TransactionMatch(
                transaction=transaction,
                duplicates=duplicates,
                is_likely_duplicate=is_likely_duplicate,
                confidence_score=confidence_score
            ))
        
        return matches
    
    async def _find_duplicate_transactions(
        self, 
        transaction: ParsedTransaction, 
        user_id: str
    ) -> List[DuplicateMatch]:
        """
        Find potential duplicate transactions using multiple matching strategies.
        
        Args:
            transaction: Transaction to check for duplicates
            user_id: User ID
            
        Returns:
            List of potential duplicate matches
        """
        duplicates = []
        
        try:
            # Define search window (±3 days from transaction date)
            date_window = timedelta(days=3)
            start_date = transaction.date - date_window
            end_date = transaction.date + date_window
            
            # Get existing expenses in the date range
            existing_expenses = await self.expense_repo.find_by_date_range(
                user_id, start_date, end_date
            )
            
            for expense in existing_expenses:
                match_score, reasons = self._calculate_match_score(transaction, expense)
                
                if match_score > 0.5:  # Only consider matches above 50%
                    duplicates.append(DuplicateMatch(
                        transaction_index=0,  # Will be set by caller
                        existing_expense_id=str(expense.id),
                        match_score=match_score,
                        match_reasons=reasons
                    ))
            
            # Sort by match score (highest first)
            duplicates.sort(key=lambda x: x.match_score, reverse=True)
            
            return duplicates[:5]  # Return top 5 matches
            
        except Exception as e:
            logger.error(f"Error finding duplicate transactions: {e}")
            return []
    
    def _calculate_match_score(
        self, 
        transaction: ParsedTransaction, 
        expense: ExpenseTable
    ) -> Tuple[float, List[str]]:
        """
        Calculate match score between a transaction and existing expense.
        
        Args:
            transaction: Parsed transaction
            expense: Existing expense
            
        Returns:
            Tuple of (match_score, list_of_reasons)
        """
        score = 0.0
        reasons = []
        
        # Exact amount match (40% weight)
        if abs(float(transaction.amount) - float(expense.amount)) < 0.01:
            score += 0.4
            reasons.append("Exact amount match")
        elif abs(float(transaction.amount) - float(expense.amount)) < 1.0:
            score += 0.2
            reasons.append("Close amount match")
        
        # Date proximity (30% weight)
        date_diff = abs((transaction.date - expense.date).days)
        if date_diff == 0:
            score += 0.3
            reasons.append("Same date")
        elif date_diff <= 1:
            score += 0.2
            reasons.append("Adjacent date")
        elif date_diff <= 3:
            score += 0.1
            reasons.append("Close date")
        
        # Description similarity (20% weight)
        desc_similarity = self._calculate_string_similarity(
            transaction.description or "", 
            expense.description or ""
        )
        if desc_similarity > 0.8:
            score += 0.2
            reasons.append("Very similar description")
        elif desc_similarity > 0.6:
            score += 0.15
            reasons.append("Similar description")
        elif desc_similarity > 0.4:
            score += 0.1
            reasons.append("Somewhat similar description")
        
        # Merchant match (10% weight)
        if (transaction.merchant and expense.merchant_id and 
            transaction.merchant.lower() in (expense.merchant.name.lower() if expense.merchant else "")):
            score += 0.1
            reasons.append("Merchant match")
        
        return min(score, 1.0), reasons
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity using simple character-based approach.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Simple character overlap calculation
        set1 = set(str1)
        set2 = set(str2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    async def rollback_import(self, rollback_token: str, user_id: str) -> bool:
        """
        Rollback a completed import using the rollback token.
        
        Args:
            rollback_token: Token from the import result
            user_id: User ID for security
            
        Returns:
            True if rollback was successful
        """
        try:
            expense_ids = self._import_rollback_data.get(rollback_token)
            if not expense_ids:
                logger.warning(f"No rollback data found for token: {rollback_token}")
                return False
            
            success = await self._rollback_expenses(expense_ids, user_id)
            
            if success:
                # Remove rollback data after successful rollback
                self._import_rollback_data.pop(rollback_token, None)
                logger.info(f"Successfully rolled back import: {rollback_token}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during import rollback: {e}")
            return False
    
    async def _rollback_expenses(self, expense_ids: List[str], user_id: str) -> bool:
        """
        Delete expenses by IDs for rollback.
        
        Args:
            expense_ids: List of expense IDs to delete
            user_id: User ID for security
            
        Returns:
            True if all expenses were deleted successfully
        """
        try:
            deleted_count = 0
            
            for expense_id in expense_ids:
                try:
                    success = await self.expense_repo.delete(expense_id, user_id)
                    if success:
                        deleted_count += 1
                    else:
                        logger.warning(f"Failed to delete expense: {expense_id}")
                except Exception as e:
                    logger.error(f"Error deleting expense {expense_id}: {e}")
            
            logger.info(f"Rolled back {deleted_count}/{len(expense_ids)} expenses")
            return deleted_count == len(expense_ids)
            
        except Exception as e:
            logger.error(f"Error in rollback expenses: {e}")
            return False
    
    async def _process_transaction(
        self,
        transaction: ParsedTransaction,
        category_mappings: Dict[str, str],
        merchant_mappings: Dict[str, str],
        user_id: str
    ) -> ParsedTransaction:
        """
        Process a transaction by applying custom mappings.
        
        Args:
            transaction: Original transaction
            category_mappings: Custom category mappings
            merchant_mappings: Custom merchant mappings
            user_id: User ID
            
        Returns:
            Processed transaction
        """
        # Apply merchant mapping
        if transaction.merchant and transaction.merchant in merchant_mappings:
            transaction.merchant = merchant_mappings[transaction.merchant]
        
        # Apply category mapping
        if transaction.category and transaction.category in category_mappings:
            transaction.category = category_mappings[transaction.category]
        
        # Ensure merchant exists (create if needed)
        if transaction.merchant:
            try:
                merchant = await self.merchant_repo.find_by_name(transaction.merchant, user_id)
                if not merchant:
                    # Create new merchant
                    from ..models.merchant import MerchantCreate
                    merchant_data = MerchantCreate(
                        name=transaction.merchant,
                        category=transaction.category
                    )
                    await self.merchant_repo.create(merchant_data, user_id)
            except Exception as e:
                logger.warning(f"Failed to create merchant {transaction.merchant}: {e}")
        
        return transaction