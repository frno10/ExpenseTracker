from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, text

from ..models.expense import ExpenseTable
from ..models.attachment import AttachmentTable
from ..core.exceptions import ValidationError


class ExpenseSearchService:
    """Service for advanced expense search functionality including notes and attachments."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== SEARCH OPERATIONS =====
    
    async def search_expenses(
        self,
        user_id: UUID,
        search_term: str,
        search_fields: Optional[List[str]] = None,
        category_ids: Optional[List[UUID]] = None,
        merchant_ids: Optional[List[UUID]] = None,
        payment_method_ids: Optional[List[UUID]] = None,
        account_ids: Optional[List[UUID]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        amount_min: Optional[Decimal] = None,
        amount_max: Optional[Decimal] = None,
        has_attachments: Optional[bool] = None,
        attachment_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_by: str = "expense_date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Advanced expense search with multiple filters and full-text search.
        
        Args:
            user_id: User ID to search expenses for
            search_term: Text to search for in description, notes, and attachments
            search_fields: Fields to search in ['description', 'notes', 'attachments']
            category_ids: Filter by category IDs
            merchant_ids: Filter by merchant IDs
            payment_method_ids: Filter by payment method IDs
            account_ids: Filter by account IDs
            date_from: Start date filter
            date_to: End date filter
            amount_min: Minimum amount filter
            amount_max: Maximum amount filter
            has_attachments: Filter by presence of attachments
            attachment_types: Filter by attachment types
            limit: Maximum number of results
            offset: Number of results to skip
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Dictionary with expenses, total count, and search metadata
        """
        # Validate search term
        if not search_term or len(search_term.strip()) < 2:
            raise ValidationError("Search term must be at least 2 characters")
        
        search_term = search_term.strip()
        
        # Default search fields
        if search_fields is None:
            search_fields = ['description', 'notes', 'attachments']
        
        # Build base query
        query = self.db.query(ExpenseTable).filter(
            ExpenseTable.user_id == user_id
        ).options(
            joinedload(ExpenseTable.category),
            joinedload(ExpenseTable.merchant),
            joinedload(ExpenseTable.payment_method),
            joinedload(ExpenseTable.account),
            joinedload(ExpenseTable.attachments)
        )
        
        # Apply text search filters
        text_filters = []
        
        if 'description' in search_fields:
            text_filters.append(ExpenseTable.description.ilike(f"%{search_term}%"))
        
        if 'notes' in search_fields:
            text_filters.append(ExpenseTable.notes.ilike(f"%{search_term}%"))
        
        if 'attachments' in search_fields:
            # Search in attachment filenames
            attachment_subquery = self.db.query(AttachmentTable.expense_id).filter(
                AttachmentTable.user_id == user_id,
                or_(
                    AttachmentTable.filename.ilike(f"%{search_term}%"),
                    AttachmentTable.original_filename.ilike(f"%{search_term}%")
                )
            ).subquery()
            
            text_filters.append(ExpenseTable.id.in_(attachment_subquery))
        
        if text_filters:
            query = query.filter(or_(*text_filters))
        
        # Apply additional filters
        if category_ids:
            query = query.filter(ExpenseTable.category_id.in_(category_ids))
        
        if merchant_ids:
            query = query.filter(ExpenseTable.merchant_id.in_(merchant_ids))
        
        if payment_method_ids:
            query = query.filter(ExpenseTable.payment_method_id.in_(payment_method_ids))
        
        if account_ids:
            query = query.filter(ExpenseTable.account_id.in_(account_ids))
        
        if date_from:
            query = query.filter(ExpenseTable.expense_date >= date_from)
        
        if date_to:
            query = query.filter(ExpenseTable.expense_date <= date_to)
        
        if amount_min is not None:
            query = query.filter(ExpenseTable.amount >= amount_min)
        
        if amount_max is not None:
            query = query.filter(ExpenseTable.amount <= amount_max)
        
        if has_attachments is not None:
            if has_attachments:
                # Has attachments
                attachment_subquery = self.db.query(AttachmentTable.expense_id).filter(
                    AttachmentTable.user_id == user_id
                ).subquery()
                query = query.filter(ExpenseTable.id.in_(attachment_subquery))
            else:
                # No attachments
                attachment_subquery = self.db.query(AttachmentTable.expense_id).filter(
                    AttachmentTable.user_id == user_id
                ).subquery()
                query = query.filter(~ExpenseTable.id.in_(attachment_subquery))
        
        if attachment_types:
            # Filter by attachment types
            attachment_subquery = self.db.query(AttachmentTable.expense_id).filter(
                AttachmentTable.user_id == user_id,
                AttachmentTable.attachment_type.in_(attachment_types)
            ).subquery()
            query = query.filter(ExpenseTable.id.in_(attachment_subquery))
        
        # Get total count before applying limit/offset
        total_count = query.count()
        
        # Apply sorting
        sort_column = getattr(ExpenseTable, sort_by, ExpenseTable.expense_date)
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        # Execute query
        expenses = query.all()
        
        # Calculate search statistics
        search_stats = await self._calculate_search_statistics(
            user_id, search_term, search_fields, expenses
        )
        
        return {
            'expenses': expenses,
            'total_count': total_count,
            'returned_count': len(expenses),
            'search_term': search_term,
            'search_fields': search_fields,
            'search_statistics': search_stats,
            'filters_applied': {
                'category_ids': category_ids,
                'merchant_ids': merchant_ids,
                'payment_method_ids': payment_method_ids,
                'account_ids': account_ids,
                'date_from': date_from,
                'date_to': date_to,
                'amount_min': amount_min,
                'amount_max': amount_max,
                'has_attachments': has_attachments,
                'attachment_types': attachment_types
            }
        }
    
    async def search_expenses_with_notes(
        self,
        user_id: UUID,
        search_term: str,
        limit: Optional[int] = None
    ) -> List[ExpenseTable]:
        """Search expenses specifically in notes field."""
        if not search_term or len(search_term.strip()) < 2:
            raise ValidationError("Search term must be at least 2 characters")
        
        query = self.db.query(ExpenseTable).filter(
            ExpenseTable.user_id == user_id,
            ExpenseTable.notes.ilike(f"%{search_term.strip()}%")
        ).options(
            joinedload(ExpenseTable.category),
            joinedload(ExpenseTable.merchant),
            joinedload(ExpenseTable.attachments)
        ).order_by(desc(ExpenseTable.expense_date))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    async def search_expenses_by_attachment_content(
        self,
        user_id: UUID,
        search_term: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search expenses by attachment filename/content."""
        if not search_term or len(search_term.strip()) < 2:
            raise ValidationError("Search term must be at least 2 characters")
        
        # Find attachments matching the search term
        attachments = self.db.query(AttachmentTable).filter(
            AttachmentTable.user_id == user_id,
            or_(
                AttachmentTable.filename.ilike(f"%{search_term.strip()}%"),
                AttachmentTable.original_filename.ilike(f"%{search_term.strip()}%")
            )
        ).options(
            joinedload(AttachmentTable.expense)
        ).all()
        
        # Group by expense
        expense_attachments = {}
        for attachment in attachments:
            expense_id = str(attachment.expense_id)
            if expense_id not in expense_attachments:
                expense_attachments[expense_id] = {
                    'expense': attachment.expense,
                    'matching_attachments': []
                }
            expense_attachments[expense_id]['matching_attachments'].append(attachment)
        
        # Convert to list and sort by expense date
        results = list(expense_attachments.values())
        results.sort(key=lambda x: x['expense'].expense_date, reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    async def get_search_suggestions(
        self,
        user_id: UUID,
        partial_term: str,
        suggestion_type: str = "all"
    ) -> Dict[str, List[str]]:
        """
        Get search suggestions based on partial input.
        
        Args:
            user_id: User ID
            partial_term: Partial search term
            suggestion_type: Type of suggestions ('all', 'descriptions', 'notes', 'merchants', 'categories')
            
        Returns:
            Dictionary with different types of suggestions
        """
        if not partial_term or len(partial_term.strip()) < 1:
            return {}
        
        partial_term = partial_term.strip()
        suggestions = {}
        
        if suggestion_type in ['all', 'descriptions']:
            # Get description suggestions
            description_results = self.db.query(ExpenseTable.description).filter(
                ExpenseTable.user_id == user_id,
                ExpenseTable.description.ilike(f"%{partial_term}%"),
                ExpenseTable.description.isnot(None)
            ).distinct().limit(10).all()
            
            suggestions['descriptions'] = [
                desc[0] for desc in description_results if desc[0]
            ]
        
        if suggestion_type in ['all', 'notes']:
            # Get notes suggestions (extract relevant snippets)
            notes_results = self.db.query(ExpenseTable.notes).filter(
                ExpenseTable.user_id == user_id,
                ExpenseTable.notes.ilike(f"%{partial_term}%"),
                ExpenseTable.notes.isnot(None)
            ).distinct().limit(10).all()
            
            # Extract snippets containing the search term
            notes_snippets = []
            for note_result in notes_results:
                note = note_result[0]
                if note:
                    # Find the position of the search term
                    lower_note = note.lower()
                    lower_term = partial_term.lower()
                    pos = lower_note.find(lower_term)
                    
                    if pos != -1:
                        # Extract snippet around the term
                        start = max(0, pos - 20)
                        end = min(len(note), pos + len(partial_term) + 20)
                        snippet = note[start:end]
                        
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(note):
                            snippet = snippet + "..."
                        
                        notes_snippets.append(snippet)
            
            suggestions['notes'] = notes_snippets
        
        if suggestion_type in ['all', 'merchants']:
            # Get merchant suggestions
            from ..models.merchant import MerchantTable
            merchant_results = self.db.query(MerchantTable.name).filter(
                MerchantTable.user_id == user_id,
                MerchantTable.name.ilike(f"%{partial_term}%")
            ).distinct().limit(10).all()
            
            suggestions['merchants'] = [
                merchant[0] for merchant in merchant_results
            ]
        
        if suggestion_type in ['all', 'categories']:
            # Get category suggestions
            from ..models.category import CategoryTable
            category_results = self.db.query(CategoryTable.name).filter(
                CategoryTable.user_id == user_id,
                CategoryTable.name.ilike(f"%{partial_term}%")
            ).distinct().limit(10).all()
            
            suggestions['categories'] = [
                category[0] for category in category_results
            ]
        
        return suggestions
    
    # ===== ANALYTICS AND STATISTICS =====
    
    async def _calculate_search_statistics(
        self,
        user_id: UUID,
        search_term: str,
        search_fields: List[str],
        results: List[ExpenseTable]
    ) -> Dict[str, Any]:
        """Calculate statistics about search results."""
        if not results:
            return {
                'total_amount': Decimal('0.00'),
                'average_amount': Decimal('0.00'),
                'date_range': None,
                'category_breakdown': [],
                'merchant_breakdown': [],
                'field_match_counts': {}
            }
        
        # Calculate totals
        total_amount = sum(expense.amount for expense in results)
        average_amount = total_amount / len(results)
        
        # Date range
        dates = [expense.expense_date for expense in results]
        date_range = {
            'earliest': min(dates),
            'latest': max(dates)
        }
        
        # Category breakdown
        category_counts = {}
        for expense in results:
            category_name = expense.category.name if expense.category else 'Uncategorized'
            category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        category_breakdown = [
            {'category': cat, 'count': count}
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Merchant breakdown
        merchant_counts = {}
        for expense in results:
            merchant_name = expense.merchant.name if expense.merchant else 'Unknown'
            merchant_counts[merchant_name] = merchant_counts.get(merchant_name, 0) + 1
        
        merchant_breakdown = [
            {'merchant': merchant, 'count': count}
            for merchant, count in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)
        ][:10]  # Top 10 merchants
        
        # Field match counts (approximate)
        field_match_counts = {}
        for field in search_fields:
            if field == 'description':
                field_match_counts['description'] = sum(
                    1 for expense in results 
                    if expense.description and search_term.lower() in expense.description.lower()
                )
            elif field == 'notes':
                field_match_counts['notes'] = sum(
                    1 for expense in results 
                    if expense.notes and search_term.lower() in expense.notes.lower()
                )
            elif field == 'attachments':
                field_match_counts['attachments'] = sum(
                    1 for expense in results 
                    if any(
                        search_term.lower() in (attachment.filename or '').lower() or
                        search_term.lower() in (attachment.original_filename or '').lower()
                        for attachment in expense.attachments
                    )
                )
        
        return {
            'total_amount': total_amount,
            'average_amount': average_amount,
            'date_range': date_range,
            'category_breakdown': category_breakdown,
            'merchant_breakdown': merchant_breakdown,
            'field_match_counts': field_match_counts
        }
    
    async def get_recent_searches(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[str]:
        """Get recent search terms for a user (would need to implement search history tracking)."""
        # This would require a search history table to implement properly
        # For now, return empty list
        return []
    
    async def get_popular_search_terms(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get popular search terms for a user (would need search history tracking)."""
        # This would require a search history table to implement properly
        # For now, return empty list
        return []