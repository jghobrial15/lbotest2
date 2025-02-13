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
        data = {}
        
        for year in years:
            data[year] = {
                'Beginning Debt': 0,
                'Interest Payment': 0,
                'Debt Paydown': 0,
                'Ending Debt': 0
            }
        
        # Set initial values for Year 0
        data['Year 0']['Beginning Debt'] = entry_debt
        data['Year 0']['Ending Debt'] = entry_debt
        
        # Calculate subsequent years
        for i in range(1, self.years + 1):
            year_col = f'Year {i}'
            prev_year_col = f'Year {i-1}'
            
            beginning_debt = data[prev_year_col]['Ending Debt']
            interest = beginning_debt * interest_rate
            debt_paydown = min(available_cash_flow[i], beginning_debt)
            ending_debt = beginning_debt - debt_paydown
            
            data[year_col]['Beginning Debt'] = beginning_debt
            data[year_col]['Interest Payment'] = interest
            data[year_col]['Debt Paydown'] = debt_paydown
            data[year_col]['Ending Debt'] = ending_debt
        
        df = pd.DataFrame(data)
        return df
    
    def calculate_cash_schedule(self, free_cash_flows, debt_paydown):
        """Calculate cash schedule with beginning cash, generation, and ending cash."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        data = {}
        
        for year in years:
            data[year] = {
                'Beginning Cash': 0,
                'Cash Generation': 0,
                'Less: Debt Paydown': 0,
                'Ending Cash': 0
            }
        
        # Calculate values for each year
        for i, year in enumerate(years):
            if i > 0:
                data[year]['Beginning Cash'] = data[years[i-1]]['Ending Cash']
            
            data[year]['Cash Generation'] = free_cash_flows[year]
            data[year]['Less: Debt Paydown'] = -debt_paydown[year]  # Negative for cash outflow
            data[year]['Ending Cash'] = (data[year]['Beginning Cash'] + 
                                       data[year]['Cash Generation'] + 
                                       data[year]['Less: Debt Paydown'])
        
        df = pd.DataFrame(data)
        return df
    
    def calculate_irr(self, entry_equity, exit_equity, cash_flows):
        """Calculate IRR based on equity flows."""
        flows = [-entry_equity] + cash_flows[1:-1].tolist() + [exit_equity]
        
        st.write("IRR Calculation Components:")
        st.write(f"Entry Equity: ${entry_equity:.1f}M")
        st.write(f"Intermediate Cash Flows: {[f'${x:.1f}M' for x in cash_flows[1:-1]]}")
        st.write(f"Exit Equity: ${exit_equity:.1f}M")
        st.write(f"Complete Flow Series: {[f'${x:.1f}M' for x in flows]}")
        
        # Check for valid IRR calculation conditions
        if not any(f < 0 for f in flows):
            st.write("Warning: No negative cash flows found - IRR calculation may fail")
        if not any(f > 0 for f in flows):
            st.write("Warning: No positive cash flows found - IRR calculation may fail")
        
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
            {year: [0, 0, 0, 0] for year in years},
            index=['Beginning Debt', 'Interest Payment', 'Debt Paydown', 'Ending Debt']
        )
        
        # Calculate initial cash flows
        initial_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule, 
            initial_debt_df,
            tax_rate, 
            capex_pct
        )
        
        # Calculate debt schedule
        debt_schedule = calculator.calculate_debt_schedule(
            entry_debt, 
            interest_rate, 
            initial_cash_flows
        )
        
        # Calculate financial schedule
        financial_schedule = calculator.calculate_financial_schedule(
            ebitda_schedule,
            debt_schedule,
            tax_rate,
            capex_pct
        )
        
        # Calculate cash schedule
        cash_schedule = calculator.calculate_cash_schedule(
            financial_schedule['Free Cash Flow'],
            debt_schedule.loc['Debt Paydown']
        )
        
        # Calculate exit values
        exit_ebitda = ebitda_schedule[-1]
        exit_tev = exit_ebitda * exit_multiple
        
        # Calculate equity values and IRRs
        entry_equity = entry_tev - entry_debt
        exit_equity = exit_tev - debt_schedule['Year 5']['Ending Debt']
        
        # Debug information about cash flows
        st.subheader("Debug Information")
        st.write("Key Values:")
        st.write(f"Entry TEV: ${entry_tev:,.1f}M")
        st.write(f"Entry Debt: ${entry_debt:,.1f}M")
        st.write(f"Entry Equity: ${entry_equity:,.1f}M")
        st.write(f"Exit TEV: ${exit_tev:,.1f}M")
        st.write(f"Exit Debt: ${debt_schedule['Year 5']['Ending Debt']:,.1f}M")
        st.write(f"Exit Equity: ${exit_equity:,.1f}M")
        
        # Show intermediate cash flows
        st.write("\nIntermediate Cash Flows:")
        yearly_flows = pd.DataFrame({
            'Year': range(calculator.years + 1),
            'Free Cash Flow ($M)': financial_schedule['Free Cash Flow'].values,
            'Debt Balance ($M)': debt_schedule.loc['Ending Debt'].values
        })
        st.dataframe(yearly_flows.round(1))
        
        # Calculate IRRs
        cash_flows = financial_schedule['Free Cash Flow'].values
        st.write("\nLevered IRR Calculation:")
        levered_irr = calculator.calculate_irr(entry_equity, exit_equity, cash_flows)
        
        st.write("\nUnlevered IRR Calculation:")
        unlevered_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule,
            initial_debt_df,
            tax_rate,
            capex_pct
        )
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
