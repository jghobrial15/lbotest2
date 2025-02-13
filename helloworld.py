[Previous code up to calculate_debt_schedule remains the same]

    def calculate_debt_schedule(self, entry_debt, interest_rate, available_cash_flow):
        """Calculate debt schedule with years as columns."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        df = pd.DataFrame(index=['Beginning Debt', 'Interest Payment', 'Debt Paydown', 'Ending Debt'])
        
        # Initialize all years with zeros
        for year in years:
            df[year] = 0.0
        
        # Set initial values for Year 0
        df.loc['Beginning Debt', 'Year 0'] = entry_debt
        df.loc['Ending Debt', 'Year 0'] = entry_debt
        
        # Calculate subsequent years
        for i in range(1, self.years + 1):
            year = f'Year {i}'
            prev_year = f'Year {i-1}'
            
            beginning_debt = df.loc['Ending Debt', prev_year]
            interest = beginning_debt * interest_rate
            
            df.loc['Beginning Debt', year] = beginning_debt
            df.loc['Interest Payment', year] = interest
            
            # Available cash for debt paydown is the cash flow minus interest payment
            available_cash_after_interest = max(0, available_cash_flow[i] - interest)
            debt_paydown = min(available_cash_after_interest, beginning_debt)
            
            df.loc['Debt Paydown', year] = debt_paydown
            df.loc['Ending Debt', year] = beginning_debt - debt_paydown
        
        return df

[Previous code until the main calculation section remains the same]

        # Calculate initial cash flows with debug output
        st.subheader("Cash Flow Analysis")
        st.write("Step 1: Initial Cash Flow Calculation")
        initial_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule, 
            initial_debt_df,
            tax_rate, 
            capex_pct
        )
        
        # Show initial cash flows
        st.write("Initial Cash Flows by Year:")
        initial_flows_df = pd.DataFrame({
            'Year': [f'Year {i}' for i in range(calculator.years + 1)],
            'EBITDA': ebitda_schedule,
            'Capex': [-e * capex_pct for e in ebitda_schedule],
            'Available Cash Flow': initial_cash_flows
        })
        st.dataframe(initial_flows_df.round(1))
        
        # Calculate debt schedule
        debt_schedule = calculator.calculate_debt_schedule(
            entry_debt, 
            interest_rate, 
            initial_cash_flows
        )
        
        # Show debt service capacity
        st.write("\nStep 2: Debt Service Analysis")
        debt_service_df = pd.DataFrame({
            'Year': [f'Year {i}' for i in range(calculator.years + 1)],
            'Available Cash Flow': initial_cash_flows,
            'Interest Payment': debt_schedule.loc['Interest Payment'],
            'Cash Available for Debt Paydown': [
                max(0, cf - ip) for cf, ip in 
                zip(initial_cash_flows, debt_schedule.loc['Interest Payment'])
            ],
            'Actual Debt Paydown': debt_schedule.loc['Debt Paydown'],
        })
        st.dataframe(debt_service_df.round(1))

[Rest of the code remains the same]
