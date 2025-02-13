import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

class LBOCalculator:
    def __init__(self):
        self.years = 5  # Fixed 5-year projection period

    def calculate_ebitda_schedule(self, entry_ebitda, ebitda_cagr):
        """Calculate EBITDA progression over the projection period."""
        return [entry_ebitda * (1 + ebitda_cagr) ** year for year in range(self.years + 1)]

    def calculate_cash_flows(self, ebitda_schedule, debt_schedule, tax_rate, capex_pct):
        """Calculate available cash flows after interest, taxes, and capex."""
        cash_flows = []
        years = [f"Year {i}" for i in range(self.years + 1)]
        
        for i, year in enumerate(years):
            ebitda = ebitda_schedule[i]
            capex = ebitda * capex_pct
            
            if i == 0:
                cash_flows.append(0)
                continue
                
            interest = debt_schedule.loc['Interest Payment', year]
            ebit = ebitda - capex
            taxes = max(0, (ebit - interest) * tax_rate)
            available_cash_flow = ebit - taxes - interest
            
            cash_flows.append(available_cash_flow)
            
        return cash_flows
        
    def calculate_financial_schedule(self, ebitda_schedule, debt_schedule, tax_rate, capex_pct):
        """Calculate full financial schedule with all metrics."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        data = {}
        
        for i, year in enumerate(years):
            ebitda = ebitda_schedule[i]
            capex = -ebitda * capex_pct  # Negative for cash outflow
            interest = -debt_schedule.loc['Interest Payment', year]  # Negative for cash outflow
            
            ebit = ebitda + capex
            ebt = ebit + interest
            taxes = -max(0, ebt * tax_rate)  # Negative for cash outflow
            net_income = ebt + taxes
            free_cash_flow = net_income - capex  # Capex already negative
            
            data[year] = {
                'EBITDA': ebitda,
                'Less: Capex': capex,
                'EBIT': ebit,
                'Less: Interest': interest,
                'EBT': ebt,
                'Less: Taxes': taxes,
                'Net Income': net_income,
                'Free Cash Flow': free_cash_flow
            }
        
        return pd.DataFrame(data).transpose()
    
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
    
    def calculate_cash_schedule(self, free_cash_flows, debt_paydown):
        """Calculate cash schedule with beginning cash, generation, and ending cash."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        df = pd.DataFrame(index=['Beginning Cash', 'Cash Generation', 'Less: Debt Paydown', 'Ending Cash'])
        
        # Initialize all years with zeros
        for year in years:
            df[year] = 0.0
        
        # Calculate values for each year
        for i, year in enumerate(years):
            if i > 0:
                df.loc['Beginning Cash', year] = df.loc['Ending Cash', years[i-1]]
            
            df.loc['Cash Generation', year] = free_cash_flows[i]
            df.loc['Less: Debt Paydown', year] = -debt_paydown[i]  # Negative for cash outflow
            df.loc['Ending Cash', year] = (df.loc['Beginning Cash', year] + 
                                         df.loc['Cash Generation', year] + 
                                         df.loc['Less: Debt Paydown', year])
        
        return df
    
    def calculate_irr(self, entry_equity, exit_equity, cash_flows):
        """Calculate IRR based on equity flows."""
        if isinstance(cash_flows, np.ndarray):
            cash_flows = cash_flows.tolist()
        
        flows = [-entry_equity] + cash_flows[1:-1] + [exit_equity]
        
        st.write("IRR Calculation Components:")
        st.write(f"Entry Equity: ${entry_equity:.1f}M")
        st.write(f"Intermediate Cash Flows: {[f'${x:.1f}M' for x in cash_flows[1:-1]]}")
        st.write(f"Exit Equity: ${exit_equity:.1f}M")
        st.write(f"Complete Flow Series: {[f'${x:.1f}M' for x in flows]}")
        
        try:
            irr = npf.irr(flows)
            if np.isnan(irr):
                st.write("IRR calculation returned NaN - falling back to 0.0")
                return 0.0
            return irr
        except Exception as e:
            st.write(f"IRR calculation failed: {str(e)}")
            return 0.0

    def calculate_irr_decomposition(self, entry_ebitda, exit_ebitda, entry_multiple, 
                                  exit_multiple, levered_irr, unlevered_irr):
        """Calculate IRR decomposition components."""
        ebitda_growth = (exit_ebitda / entry_ebitda) ** (1/self.years) - 1
        multiple_change = (exit_multiple / entry_multiple) ** (1/self.years) - 1
        tev_growth = (1 + ebitda_growth) * (1 + multiple_change) - 1
        yield_component = 1 / entry_multiple
        covariance = unlevered_irr - (tev_growth + yield_component)
        leverage_impact = levered_irr - unlevered_irr
        
        return {
            'EBITDA Growth': ebitda_growth,
            'Multiple Change': multiple_change,
            'TEV Growth': tev_growth,
            'Yield': yield_component,
            'Covariance': covariance,
            'Unlevered IRR': unlevered_irr,
            'Leverage Impact': leverage_impact,
            'Levered IRR': levered_irr
        }

def main():
    st.title("LBO Model Calculator")
    
    # Input Section
    st.header("Input Assumptions")
    col1, col2 = st.columns(2)
    
    with col1:
        entry_ebitda = st.number_input("Entry EBITDA ($M)", value=100.0)
        ebitda_cagr = st.number_input("EBITDA CAGR (%)", value=10.0) / 100
        entry_tev = st.number_input("Entry TEV ($M)", value=2000.0)
        exit_multiple = st.number_input("Exit Multiple", value=19.0)
    
    with col2:
        entry_debt = st.number_input("Entry Debt ($M)", value=800.0)
        tax_rate = st.number_input("Tax Rate (%)", value=25.0) / 100
        interest_rate = st.number_input("Interest Rate (%)", value=8.0) / 100
        capex_pct = st.number_input("Capex as % of EBITDA (%)", value=10.0) / 100
    
    calculator = LBOCalculator()
    
    if st.button("Calculate IRR"):
        # Core calculations
        entry_multiple = entry_tev / entry_ebitda
        ebitda_schedule = calculator.calculate_ebitda_schedule(entry_ebitda, ebitda_cagr)
        
        # Create initial debt schedule for first cash flow calculation
        years = [f"Year {i}" for i in range(calculator.years + 1)]
        initial_debt_df = pd.DataFrame(
            index=['Beginning Debt', 'Interest Payment', 'Debt Paydown', 'Ending Debt'],
            columns=years,
            data=np.zeros((4, calculator.years + 1))
        )
        
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
        
        # Calculate financial schedule
        financial_schedule = calculator.calculate_financial_schedule(
            ebitda_schedule,
            debt_schedule,
            tax_rate,
            capex_pct
        )
        
        # Calculate exit values
        exit_ebitda = ebitda_schedule[-1]
        exit_tev = exit_ebitda * exit_multiple
        
        # Calculate equity values and IRRs
        entry_equity = entry_tev - entry_debt
        exit_equity = exit_tev - debt_schedule.loc['Ending Debt', 'Year 5']
        
        # Exit value calculation debug
        st.subheader("Exit Value Bridge")
        st.write("Step 1: EBITDA Growth")
        st.write(f"Entry EBITDA: ${entry_ebitda:.1f}M")
        st.write(f"EBITDA CAGR: {ebitda_cagr:.1%}")
        st.write(f"Exit EBITDA: ${exit_ebitda:.1f}M")
        
        st.write("\nStep 2: Exit TEV Calculation")
        st.write(f"Exit Multiple: {exit_multiple:.1f}x")
        st.write(f"Exit TEV = Exit EBITDA × Exit Multiple")
        st.write(f"Exit TEV = ${exit_ebitda:.1f}M × {exit_multiple:.1f}x = ${exit_tev:.1f}M")
        
        st.write("\nStep 3: Exit Equity Calculation")
        exit_debt = debt_schedule.loc['Ending Debt', 'Year 5']
        st.write(f"Exit Debt (Year 5 Ending Debt): ${exit_debt:.1f}M")
        st.write(f"Exit Equity = Exit TEV - Exit Debt")
        st.write(f"Exit Equity = ${exit_tev:.1f}M - ${exit_debt:.1f}M = ${exit_equity:.1f}M")
        
        # Equity returns summary
        st.write("\nEquity Returns Summary:")
        st.write(f"Entry Equity: ${entry_equity:.1f}M")
        st.write(f"Exit Equity: ${exit_equity:.1f}M")
        total_return = (exit_equity / entry_equity - 1) * 100
        st.write(f"Total Return: {total_return:.1f}%")
        
        # Calculate unlevered values
        unlevered_entry_equity = entry_tev  # For unlevered, entry equity equals TEV
        unlevered_exit_equity = exit_tev    # For unlevered, exit equity equals TEV
        unlevered_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule,
            initial_debt_df,
            tax_rate,
            capex_pct
        )
        
        # Calculate IRRs
        st.write("\nLevered IRR Calculation:")
        cash_flows = financial_schedule['Free Cash Flow'].values
        levered_irr = calculator.calculate_irr(entry_equity, exit_equity, cash_flows)
        
        st.write("\nUnlevered IRR Calculation:")
        unlevered_irr = calculator.calculate_irr(
            unlevered_entry_equity, 
            unlevered_exit_equity, 
            unlevered_cash_flows
        )
        
        # Display Results
        st.header("Results")
        
        # Financial Schedule
        st.subheader("Financial Schedule ($M)")
        st.dataframe(financial_schedule.round(1))
        
        # Debt Schedule
        st.subheader("Debt Schedule ($M)")
        st.dataframe(debt_schedule.round(1))
        
        # Cash Schedule
        st.subheader("Cash Schedule ($M)")
        cash_schedule = calculator.calculate_cash_schedule(
            financial_schedule['Free Cash Flow'].values,
            debt_schedule.loc['Debt Paydown'].values
        )
        st.dataframe(cash_schedule.round(1))
        
        # IRR Results
        st.subheader("IRR Results")
        st.write(f"Levered IRR: {levered_irr:.1%}")
        st.write(f"Unlevered IRR: {unlevered_irr:.1%}")
        
        # IRR Decomposition
        st.subheader("IRR Decomposition")
        decomposition = calculator.calculate_irr_decomposition(
            entry_ebitda,
            exit_ebitda,
            entry_multiple,
            exit_multiple,
            levered_irr,
            unlevered_irr
        )
        
        decomposition_df = pd.DataFrame(
            list(decomposition.items()),
            columns=['Component', 'Value']
        )
        decomposition_df['Value'] = decomposition_df['Value'].apply(lambda x: f"{x:.1%}")
        st.table(decomposition_df)

if __name__ == "__main__":
    main()
