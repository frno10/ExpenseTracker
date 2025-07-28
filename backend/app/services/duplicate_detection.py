"""
Duplicate detection service for statement imports.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from ..models.expense import ExpenseTable
from ..parsers.base import ParsedTransaction
from ..repositories.expense import ExpenseRepository

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Service for detecting duplicate transactions during import."""
    
    def __init__(self):
        self.expense_repo = ExpenseRepository()
    
    async def find_potential_duplicates(
        self,
        transaction: ParsedTransaction,
        user_id: str,
        tolerance_days: int = 3,
        amount_tolerance: Decimal = Decimal("0.01")
    ) -> List[ExpenseTable]:
        """
        Find potential duplicate expenses for a parsed transaction.
        
        Args:
            transaction: Parsed transaction to check
            user_id: User ID to scope the search
            tolerance_days: Number of days to search around the transaction date
            amount_tolerance: Amount tolerance for matching
            
        Returns:
            List of potentially duplicate expenses
        """
        try:
            # Define date range for search
            start_date = transaction.date - timedelta(days=tolerance_days)
            end_date = transaction.date + timedelta(days=tolerance_days)
            
            # Define amount range
            min_amount = transaction.amount - amount_tolerance
            max_amount = transaction.amount + amount_tolerance
            
            # Search for similar expenses (placeholder - would need database session)
            # For now, return empty list since we don't have a database session
            similar_expenses = []
            
            # Score and filter potential duplicates
            potential_duplicates = []
            for expense in similar_expenses:
                score = self._calculate_similarity_score(transaction, expense)
                if score >= 0.7:  # 70% similarity threshold
                    potential_duplicates.append(expense)
            
            # Sort by similarity score (highest first)
            potential_duplicates.sort(
                key=lambda e: self._calculate_similarity_score(transaction, e),
                reverse=True
            )
            
            return potential_duplicates
            
        except Exception as e:
            logger.error(f"Error finding potential duplicates: {e}")
            return []
    
    async def is_likely_duplicate(
        self,
        transaction: ParsedTransaction,
        user_id: str,
        threshold: float = 0.8
    ) -> bool:
        """
        Check if a transaction is likely a duplicate.
        
        Args:
            transaction: Parsed transaction to check
            user_id: User ID to scope the search
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if likely duplicate, False otherwise
        """
        potential_duplicates = await self.find_potential_duplicates(transaction, user_id)
        
        if not potential_duplicates:
            return False
        
        # Check if the highest scoring match exceeds threshold
        highest_score = self._calculate_similarity_score(transaction, potential_duplicates[0])
        return highest_score >= threshold
    
    def _extract_keywords(self, description: str) -> List[str]:
        """
        Extract keywords from transaction description for matching.
        
        Args:
            description: Transaction description
            
        Returns:
            List of keywords
        """
        if not description:
            return []
        
        # Simple keyword extraction
        # Remove common words and split
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'purchase', 'payment',
            'transaction', 'debit', 'credit', 'card', 'pos', 'atm'
        }
        
        words = description.lower().split()
        keywords = [
            word.strip('.,!?;:()[]{}"\'-')
            for word in words
            if len(word) > 2 and word.lower() not in stop_words
        ]
        
        return keywords[:10]  # Limit to first 10 keywords
    
    def _calculate_similarity_score(
        self,
        transaction: ParsedTransaction,
        expense: ExpenseTable
    ) -> float:
        """
        Calculate similarity score between a parsed transaction and an existing expense.
        
        Args:
            transaction: Parsed transaction
            expense: Existing expense
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        score = 0.0
        weight_sum = 0.0
        
        # Amount similarity (weight: 0.4)
        amount_weight = 0.4
        if transaction.amount == expense.amount:
            score += amount_weight
        else:
            # Partial score based on how close amounts are
            diff = abs(float(transaction.amount - expense.amount))
            max_amount = max(abs(float(transaction.amount)), abs(float(expense.amount)))
            if max_amount > 0:
                amount_similarity = max(0, 1 - (diff / max_amount))
                score += amount_weight * amount_similarity
        weight_sum += amount_weight
        
        # Date similarity (weight: 0.3)
        date_weight = 0.3
        date_diff = abs((transaction.date - expense.expense_date).days)
        if date_diff == 0:
            score += date_weight
        elif date_diff <= 3:
            # Partial score for dates within 3 days
            date_similarity = max(0, 1 - (date_diff / 3))
            score += date_weight * date_similarity
        weight_sum += date_weight
        
        # Description similarity (weight: 0.3)
        desc_weight = 0.3
        desc_similarity = self._calculate_text_similarity(
            transaction.description or "",
            expense.description or ""
        )
        score += desc_weight * desc_similarity
        weight_sum += desc_weight
        
        # Normalize score
        return score / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using simple word overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Extract keywords from both texts
        keywords1 = set(self._extract_keywords(text1))
        keywords2 = set(self._extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0


class ImportConflictResolver:
    """Service for resolving conflicts during import."""
    
    def __init__(self):
        self.duplicate_detector = DuplicateDetectionService()
    
    async def resolve_duplicates(
        self,
        transactions: List[ParsedTransaction],
        user_id: str,
        auto_skip_duplicates: bool = True
    ) -> tuple[List[ParsedTransaction], List[dict]]:
        """
        Resolve duplicate conflicts in a list of transactions.
        
        Args:
            transactions: List of parsed transactions
            user_id: User ID
            auto_skip_duplicates: Whether to automatically skip likely duplicates
            
        Returns:
            Tuple of (clean_transactions, conflict_reports)
        """
        clean_transactions = []
        conflict_reports = []
        
        for i, transaction in enumerate(transactions):
            try:
                # Check for duplicates
                potential_duplicates = await self.duplicate_detector.find_potential_duplicates(
                    transaction, user_id
                )
                
                if potential_duplicates:
                    highest_score = self.duplicate_detector._calculate_similarity_score(
                        transaction, potential_duplicates[0]
                    )
                    
                    conflict_report = {
                        "transaction_index": i,
                        "transaction": {
                            "date": transaction.date.isoformat(),
                            "description": transaction.description,
                            "amount": float(transaction.amount)
                        },
                        "potential_duplicates": [
                            {
                                "expense_id": str(dup.id),
                                "date": dup.date.isoformat(),
                                "description": dup.description,
                                "amount": float(dup.amount),
                                "similarity_score": self.duplicate_detector._calculate_similarity_score(
                                    transaction, dup
                                )
                            }
                            for dup in potential_duplicates[:3]  # Top 3 matches
                        ],
                        "recommended_action": "skip" if highest_score >= 0.8 else "review"
                    }
                    
                    conflict_reports.append(conflict_report)
                    
                    # Auto-skip if configured and high confidence
                    if auto_skip_duplicates and highest_score >= 0.8:
                        continue
                
                # Add to clean transactions if no conflicts or not auto-skipping
                clean_transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"Error resolving duplicates for transaction {i}: {e}")
                # Include transaction if error occurs
                clean_transactions.append(transaction)
        
        return clean_transactions, conflict_reports