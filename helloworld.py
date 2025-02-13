import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

class LBOCalculator:
    def __init__(self):
        self.years = 5  # Fixed 5-year projection period

    def calculate_ebitda_schedule(self, entry_ebitda, ebitda_cagr):
        """Calculate EBITDA schedule based on growth rate."""
        ebitda_schedule = []
        for year in range(self.years + 1):
            ebitda = entry_ebitda * (1 + ebitda_cagr) ** year
            ebitda_schedule.append(ebitda)
        return ebitda_schedule

    def calculate_cash_flows(self, ebitda_schedule, debt_schedule, tax_rate, capex_pct):
        """Calculate available cash flows after interest, taxes, and capex."""
        cash_flows = []
        
        for year in range(self.years + 1):
            ebitda = ebitda_schedule[year]
            capex = ebitda * capex_pct
            
            if year == 0:
                cash_flows.append(0)
                continue
                
            interest = debt_schedule.loc[year, 'interest_payment']
            ebit = ebitda - capex
            taxes = max(0, (ebit - interest) * tax_rate)
            available_cash_flow = ebit - taxes - interest
            
            cash_flows.append(available_cash_flow)
            
        return cash_flows
        
    def calculate_financial_schedule(self, ebitda_schedule, debt_schedule, tax_rate, capex_pct):
        """Calculate full financial schedule with all metrics."""
        schedule = {}
        years = [f"Year {i}" for i in range(self.years + 1)]
        
        # EBITDA
        schedule['EBITDA'] = ebitda_schedule
        
        # Less: Capex
        schedule['Less: Capex'] = [-ebitda * capex_pct for ebitda in ebitda_schedule]
        
        # EBIT
        schedule['EBIT'] = [ebitda + capex for ebitda, capex in zip(schedule['EBITDA'], schedule['Less: Capex'])]
        
        # Less: Interest
        schedule['Less: Interest'] = debt_schedule['interest_payment'].tolist()
        
        # EBT
        schedule['EBT'] = [ebit - interest for ebit, interest in zip(schedule['EBIT'], schedule['Less: Interest'])]
        
        # Less: Taxes
        schedule['Less: Taxes'] = [max(0, ebt * tax_rate) for ebt in schedule['EBT']]
        
        # Net Income
        schedule['Net Income'] = [ebt - tax for ebt, tax in zip(schedule['EBT'], schedule['Less: Taxes'])]
        
        # Free Cash Flow
        schedule['Free Cash Flow'] = [ni - capex for ni, capex in zip(schedule['Net Income'], schedule['Less: Capex'])]
        
        return pd.DataFrame(schedule, columns=years)
    
    def calculate_debt_schedule(self, entry_debt, interest_rate, available_cash_flow):
        """Calculate debt schedule with years as columns."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        schedule = {
            'Beginning Debt': [0.0] * (self.years + 1),
            'Interest Payment': [0.0] * (self.years + 1),
            'Debt Paydown': [0.0] * (self.years + 1),
            'Ending Debt': [0.0] * (self.years + 1)
        }
        
        # Initialize year 0
        schedule['Beginning Debt'][0] = entry_debt
        schedule['Ending Debt'][0] = entry_debt
        
        # Calculate subsequent years
        for year in range(1, self.years + 1):
            schedule['Beginning Debt'][year] = schedule['Ending Debt'][year-1]
            schedule['Interest Payment'][year] = schedule['Beginning Debt'][year] * interest_rate
            schedule['Debt Paydown'][year] = min(available_cash_flow[year], schedule['Beginning Debt'][year])
            schedule['Ending Debt'][year] = schedule['Beginning Debt'][year] - schedule['Debt Paydown'][year]
        
        return pd.DataFrame(schedule, columns=years)
    
    def calculate_cash_schedule(self, free_cash_flows, debt_paydown):
        """Calculate cash schedule with beginning cash, generation, and ending cash."""
        years = [f"Year {i}" for i in range(self.years + 1)]
        schedule = {
            'Beginning Cash': [0.0] * (self.years + 1),
            'Cash Generation': [0.0] * (self.years + 1),
            'Less: Debt Paydown': [0.0] * (self.years + 1),
            'Ending Cash': [0.0] * (self.years + 1)
        }
        
        for year in range(self.years + 1):
            if year > 0:
                schedule['Beginning Cash'][year] = schedule['Ending Cash'][year-1]
            schedule['Cash Generation'][year] = free_cash_flows[year]
            schedule['Less: Debt Paydown'][year] = -debt_paydown[year]  # Negative to show cash outflow
            schedule['Ending Cash'][year] = (schedule['Beginning Cash'][year] + 
                                          schedule['Cash Generation'][year] + 
                                          schedule['Less: Debt Paydown'][year])
        
        return pd.DataFrame(schedule, columns=years)
    
    def calculate_irr(self, entry_equity, exit_equity, cash_flows):
        """Calculate IRR based on equity flows."""
        flows = [-entry_equity] + cash_flows[1:-1] + [exit_equity]
        try:
            return npf.irr(flows)
        except:
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
        initial_debt_df = pd.DataFrame(
            {'interest_payment': [0.0] * (calculator.years + 1)},
            index=range(calculator.years + 1)
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
            financial_schedule['Free Cash Flow'].values,
            debt_schedule.loc['Debt Paydown']
        )
        
        # Calculate exit values
        exit_ebitda = ebitda_schedule[-1]
        exit_tev = exit_ebitda * exit_multiple
        
        # Calculate equity values and IRRs
        entry_equity = entry_tev - entry_debt
        exit_equity = exit_tev - debt_schedule.iloc[-1]['Ending Debt']
        
        cash_flows = financial_schedule['Free Cash Flow'].values
        levered_irr = calculator.calculate_irr(entry_equity, exit_equity, cash_flows)
        
        # Calculate unlevered IRR
        unlevered_entry_equity = entry_tev
        unlevered_exit_equity = exit_tev
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
