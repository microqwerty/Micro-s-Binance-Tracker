    def update_orders(self, orders: List[Dict], include_orders: Dict[int, bool]) -> None:
        """
        Update table with order data.
        
        Args:
            orders: List of order dictionaries
            include_orders: Dictionary mapping order IDs to boolean (True to include in calculations)
        """
        # Clear table
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        
        # See if we should include the trading pair column (for consolidated view)
        show_pair_column = any('originalSymbol' in order for order in orders)
        
        # Configure columns if needed
        if show_pair_column and len(self.treeview['columns']) == 5:
            # Add pair column
            self.treeview['columns'] = ('time', 'side', 'pair', 'quantity', 'price', 'total')
            self.treeview.heading('pair', text='Pair')
            self.treeview.column('pair', width=100)
        elif not show_pair_column and len(self.treeview['columns']) == 6:
            # Remove pair column
            self.treeview['columns'] = ('time', 'side', 'quantity', 'price', 'total')
        
        # Add orders to table
        for order in orders:
            # Get order ID
            order_id = order.get('orderId', 0)
            
            # Get order type
            side = order.get('side', '')
            
            # Skip orders not included in non-consolidated view
            if include_orders and (order_id not in include_orders or not include_orders[order_id]):
                continue
            
            # Format values
            if show_pair_column:
                # For consolidated view, show original trading pair
                original_symbol = order.get('originalSymbol', '')
                
                # Use normalized values if available
                price = order.get('normalizedPrice', order.get('avgPrice', 0))
                total = order.get('normalizedTotal', order.get('cummulativeQuoteQty', 0))
                
                values = [
                    order.get('time', ''),
                    side,
                    original_symbol,
                    f"{order.get('executedQty', 0):.8f}".rstrip('0').rstrip('.'),
                    f"{price:.8f}".rstrip('0').rstrip('.'),
                    f"{total:.8f}".rstrip('0').rstrip('.')
                ]
            else:
                # Regular view
                values = [
                    order.get('time', ''),
                    side,
                    f"{order.get('executedQty', 0):.8f}".rstrip('0').rstrip('.'),
                    f"{order.get('avgPrice', 0):.8f}".rstrip('0').rstrip('.'),
                    f"{order.get('cummulativeQuoteQty', 0):.8f}".rstrip('0').rstrip('.')
                ]
            
            # Add to table
            item_id = self.treeview.insert("", "end", values=values)
            
            # Color based on side
            if side == 'BUY':
                self.treeview.item(item_id, tags=('buy',))
            elif side == 'SELL':
                self.treeview.item(item_id, tags=('sell',))
            
            # Store order ID in item
            self.treeview.item(item_id, text=str(order_id))
