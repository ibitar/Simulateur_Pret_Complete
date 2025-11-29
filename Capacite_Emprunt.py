# Configuration de la page Streamlit
import streamlit as st

st.set_page_config(
    page_title="Simulateur de prêt immobilier",
    layout="wide",
    initial_sidebar_state="expanded",
)

import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from fpdf import FPDF
import tempfile
from datetime import datetime

RENTAL_INCOME_HAIRCUT = 0.80  # proportion des revenus locatifs retenue dans le scénario majoré

# --- Pied de page / Informations version ---
st.sidebar.markdown("---")
st.sidebar.caption("🛠️ Développé par **I. Bitar**")
st.sidebar.caption("📅 Dernière mise à jour : **18 octobre 2025**")
st.sidebar.caption("🔢 Version : **v1.3.0**")

st.markdown("---")
st.caption("🛠️ Développé par **I. Bitar** · 📅 Dernière mise à jour : **18 octobre 2025** · 🔢 Version : **v1.3.0**")

# Fonction pour calculer la capacité d'emprunt
def plot_borrowing_capacity(interest_rate, years, down_payment):
    loan_amounts = np.arange(150000, 500001, 10000)
    months = years * 12
    monthly_interest_rate = interest_rate / 100 / 12

    monthly_payments = []
    for loan in loan_amounts:
        loan -= down_payment
        if loan <= 0:
            monthly_payments.append(0)
        else:
            payment = loan * (monthly_interest_rate * (1 + monthly_interest_rate) ** months) / \
                      ((1 + monthly_interest_rate) ** months - 1)
            monthly_payments.append(payment)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(loan_amounts, monthly_payments, marker='o', linestyle='-', color='b')
    ax.set_title(f"Capacité d'emprunt\nTaux : {interest_rate:.2f} % | Durée : {years} ans | Apport : {down_payment:,.0f} €")
    ax.set_xlabel('Montant du prêt (€)')
    ax.set_ylabel('Mensualité du prêt (€)')
    ax.grid(True)
    return fig

# Fonction pour calculer les revenus requis
def calculate_income_requirements(monthly_payments, debt_ratio, net_to_gross_ratio,
                                  existing_mortgage_payment=0.0, rental_income=0.0):
    adjusted_payments = [max(payment + existing_mortgage_payment - rental_income, 0) for payment in monthly_payments]
    required_monthly_net_incomes = [payment / debt_ratio for payment in adjusted_payments]
    required_annual_net_incomes = [income * 12 for income in required_monthly_net_incomes]
    required_monthly_gross_incomes = [income / net_to_gross_ratio for income in required_monthly_net_incomes]
    required_annual_gross_incomes = [income * 12 for income in required_monthly_gross_incomes]

    return {
        "adjusted_monthly_charge": adjusted_payments,
        "monthly_net": required_monthly_net_incomes,
        "annual_net": required_annual_net_incomes,
        "monthly_gross": required_monthly_gross_incomes,
        "annual_gross": required_annual_gross_incomes
    }

def evaluate_bank_acceptance(combined_monthly_charge, debt_ratio, current_net_income):
    if current_net_income <= 0:
        return None, "Aucun revenu net mensuel renseigné, impossible d'évaluer l'acceptation."

    actual_ratio = combined_monthly_charge / current_net_income
    if actual_ratio <= debt_ratio:
        return actual_ratio, (
            f"Acceptation probable : ratio d'endettement estimé à {actual_ratio:.2%}, en dessous du seuil cible de {debt_ratio:.0%}."
        )
    return actual_ratio, (
        f"Attention : ratio d'endettement estimé à {actual_ratio:.2%}, supérieur au seuil cible de {debt_ratio:.0%}. "
        "Un ajustement (apport, revenus, durée…) peut être nécessaire."
    )

def compute_ratio_scenarios(
    monthly_payment,
    existing_mortgage_payment,
    rental_income,
    current_net_income,
    debt_ratio,
    rental_haircut=RENTAL_INCOME_HAIRCUT,
):
    monthly_payment = max(monthly_payment, 0)
    existing_mortgage_payment = max(existing_mortgage_payment, 0)
    rental_income = max(rental_income, 0)
    current_net_income = max(current_net_income, 0)

    combined_charge_nette = max(monthly_payment + existing_mortgage_payment - rental_income, 0)
    ratio_nette = combined_charge_nette / current_net_income if current_net_income > 0 else None

    adjusted_income = current_net_income + rental_income * rental_haircut
    total_credit_charge = monthly_payment + existing_mortgage_payment
    ratio_majoration = total_credit_charge / adjusted_income if adjusted_income > 0 else None
    max_monthly_capacity = adjusted_income * debt_ratio - existing_mortgage_payment

    if ratio_majoration is None:
        majoration_message = "Aucun revenu net mensuel renseigné, impossible d'estimer le ratio majoré."
    elif ratio_majoration <= debt_ratio:
        majoration_message = (
            f"Acceptation probable : ratio majoré estimé à {ratio_majoration:.2%}, en dessous du seuil de {debt_ratio:.0%}."
        )
    else:
        majoration_message = (
            f"Attention : ratio majoré estimé à {ratio_majoration:.2%}, supérieur au seuil de {debt_ratio:.0%}. "
            "Ajustez éventuellement apport, revenus ou durée."
        )

    return {
        "nette": {
            "charge": combined_charge_nette,
            "ratio": ratio_nette,
            "message": evaluate_bank_acceptance(combined_charge_nette, debt_ratio, current_net_income)[1]
            if current_net_income > 0
            else "Aucun revenu net mensuel renseigné, impossible d'évaluer l'acceptation.",
        },
        "majoration": {
            "adjusted_income": adjusted_income,
            "total_charge": total_credit_charge,
            "ratio": ratio_majoration,
            "max_capacity": max_monthly_capacity,
            "message": majoration_message,
            "haircut": rental_haircut,
        },
    }

# Fonction pour générer le rapport de prêt
def generate_loan_report(property_value, interest_rate, years, down_payment, debt_ratio,
                         net_to_gross_ratio, notary_fee_rate, insurance_choice,
                         insurance_rate, insurance_amount, existing_mortgage_payment=0.0,
                         rental_income=0.0, current_net_income=0.0):
    # Calcul des frais de notaire
    notary_fees = property_value * notary_fee_rate / 100
    project_cost = property_value + notary_fees  # Coût total du projet
    loan_amount = project_cost - down_payment  # Montant à emprunter

    if loan_amount <= 0:
        st.write("L'apport couvre ou dépasse le montant total du projet. Aucun prêt requis.")
        return

    months = years * 12
    monthly_interest_rate = interest_rate / 100 / 12
    monthly_payment_bank = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** months) / \
                          ((1 + monthly_interest_rate) ** months - 1)

    if insurance_choice == "Taux (%)":
        insurance_per_month = loan_amount * insurance_rate / 100 / 12
    elif insurance_choice == "Montant fixe (€)":
        insurance_per_month = insurance_amount
    else:
        insurance_per_month = 0

    monthly_payment = monthly_payment_bank + insurance_per_month

    # Calcul du coût total du prêt
    total_paid = monthly_payment * months  # Total payé sur la durée du prêt (avec assurance)
    total_interest = (monthly_payment_bank * months) - loan_amount  # Intérêts cumulés

    combined_monthly_charge = max(monthly_payment + existing_mortgage_payment - rental_income, 0)
    required_monthly_net_income = combined_monthly_charge / debt_ratio
    required_annual_net_income = required_monthly_net_income * 12
    required_monthly_gross_income = required_monthly_net_income / net_to_gross_ratio
    required_annual_gross_income = required_annual_net_income / net_to_gross_ratio
    ratio_scenarios = compute_ratio_scenarios(
        monthly_payment,
        existing_mortgage_payment,
        rental_income,
        current_net_income,
        debt_ratio,
    )
    
    # Informations sur le bien
    st.markdown("#### 🏠 Informations sur le bien")
    st.write(f"- **Valeur du bien :** {property_value:.2f} €")
    st.write(f"- **Frais de notaire ({notary_fee_rate:.2f}%) :** {notary_fees:.2f} €")
    st.write(f"- **Coût total du projet :** {project_cost:.2f} €")
    st.write(f"- **Apport initial :** {down_payment:.2f} €")

    # Montant emprunté et mensualité
    st.markdown("#### 💰 Montant emprunté et mensualité")
    st.write(f"- **Montant à emprunter :** {loan_amount:.2f} €")
    st.write(f"- **Mensualité (hors assurance) :** {monthly_payment_bank:.2f} €")
    if insurance_per_month:
        st.write(f"- **Assurance mensuelle :** {insurance_per_month:.2f} €")
    st.write(f"- **Mensualité totale :** {monthly_payment:.2f} €")
    if existing_mortgage_payment > 0:
        st.write(f"- **Crédit immobilier actuel :** {existing_mortgage_payment:.2f} € / mois")
    if rental_income > 0:
        st.write(f"- **Revenu locatif estimé :** {rental_income:.2f} € / mois")
    if current_net_income > 0:
        st.write(f"- **Charge nette prise en compte :** {combined_monthly_charge:.2f} € / mois")
        st.write(f"- **Revenu net mensuel actuel renseigné :** {current_net_income:.2f} €")
    else:
        st.write(f"- **Charge nette prise en compte :** {combined_monthly_charge:.2f} € / mois")
    st.write(
        f"💡 La mensualité a été calculée sur la base d'un taux d'intérêt de **{interest_rate:.2f}%** et d'une durée de prêt de **{years} ans**."
    )

    st.markdown("#### 🏦 Analyse d'acceptation bancaire")
    scenario_nette = ratio_scenarios["nette"]
    scenario_majoration = ratio_scenarios["majoration"]
    col_nette, col_majoration = st.columns(2)
    with col_nette:
        st.markdown("**Scénario 1 · Charge nette**")
        if scenario_nette["ratio"] is not None:
            st.write(f"- Ratio calculé : {scenario_nette['ratio']:.2%}")
            st.write(f"- Seuil cible : {debt_ratio:.0%}")
        st.write(scenario_nette["message"])
        st.markdown(
            "\n".join(
                [
                    f"- Mensualité projet (assurance incluse) : {monthly_payment:.2f} €",
                    f"- Crédit immobilier en cours ajouté : {existing_mortgage_payment:.2f} €",
                    f"- Revenu locatif déduit : {rental_income:.2f} €",
                    f"- Charge nette utilisée : {combined_monthly_charge:.2f} €",
                    f"- Revenu net mensuel déclaré : {current_net_income:.2f} €",
                ]
            )
        )
    with col_majoration:
        st.markdown("**Scénario 2 · Revenu majoré**")
        adjusted_income = scenario_majoration["adjusted_income"]
        total_charge = scenario_majoration["total_charge"]
        ratio_majoration = scenario_majoration["ratio"]
        max_capacity = scenario_majoration["max_capacity"]
        haircut_display = scenario_majoration["haircut"] * 100

        st.write(f"- Revenu retenu (incluant {haircut_display:.0f}% des loyers) : {adjusted_income:.2f} €")
        st.write(f"- Charges crédits (projet + existant) : {total_charge:.2f} €")
        if ratio_majoration is not None:
            st.write(f"- Ratio calculé : {ratio_majoration:.2%}")
            st.write(f"- Seuil cible : {debt_ratio:.0%}")
        else:
            st.write("➡️ Renseignez un revenu net mensuel ou locatif pour ce scénario.")
        st.write(scenario_majoration["message"])
        st.write(f"- Budget mensuel max pour le projet (après crédit en cours) : {max_capacity:.2f} €")

    # Revenus requis
    st.markdown("#### 📊 Revenus requis")
    col1, col2 = st.columns(2)
    col1.write(f"- **Revenu net mensuel requis :** {required_monthly_net_income:.2f} €")
    col1.write(f"- **Revenu net annuel requis :** {required_annual_net_income:.2f} €")
    col2.write(f"- **Revenu brut mensuel requis :** {required_monthly_gross_income:.2f} €")
    col2.write(f"- **Revenu brut annuel requis :** {required_annual_gross_income:.2f} €")

    # Coût total du prêt
    st.markdown("#### 🏦 Coût total du prêt")
    st.write(f"- **Coût total du prêt (incluant les intérêts) :** {total_paid:.2f} €")
    st.write(f"- **Intérêts totaux sur la durée du prêt :** {total_interest:.2f} €")

# Fonction pour convertir un DataFrame en CSV
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Fonction pour générer un tableau d'amortissement
def generate_amortization_schedule(loan_amount, interest_rate, years, monthly_insurance=0):
    months = years * 12
    monthly_rate = interest_rate / 100 / 12
    payment_bank = loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    balance = loan_amount
    schedule = []
    for m in range(1, months + 1):
        interest = balance * monthly_rate
        principal = payment_bank - interest
        balance -= principal
        schedule.append({
            "Mois": m,
            "Mensualité": payment_bank + monthly_insurance,
            "Capital": principal,
            "Intérêt": interest,
            "Assurance": monthly_insurance,
            "Solde restant": max(balance, 0)
        })
        if balance <= 0:
            break
    return pd.DataFrame(schedule)

# Simulation avec remboursement anticipé
def simulate_prepayment(loan_amount, interest_rate, years, extra_payment, start_month, monthly_insurance=0):
    months = years * 12
    monthly_rate = interest_rate / 100 / 12
    payment_bank = loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    balance = loan_amount
    schedule = []
    m = 1
    while balance > 0:
        interest = balance * monthly_rate
        principal = payment_bank - interest
        if m >= start_month:
            principal += extra_payment
        if principal > balance:
            principal = balance
        balance -= principal
        total_payment = payment_bank + monthly_insurance
        if m >= start_month:
            total_payment += extra_payment
        schedule.append({
            "Mois": m,
            "Mensualité": total_payment,
            "Capital": principal,
            "Intérêt": interest,
            "Assurance": monthly_insurance,
            "Solde restant": max(balance, 0)
        })
        m += 1
        if m > months * 2:
            break
    return pd.DataFrame(schedule)

# Fonction pour générer le PDF
def generate_pdf_report(property_value, interest_rate, years, down_payment, debt_ratio, net_to_gross_ratio, notary_fee_rate,
                        monthly_payment, loan_amount, total_paid, total_interest, notary_fees, project_cost,
                        insurance_per_month, combined_monthly_charge, existing_mortgage_payment, rental_income,
                        total_insurance_cost, total_ancillary_fees, grand_total_cost, current_net_income, ratio_scenarios):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Titre
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Rapport détaillé - Simulateur de prêt immobilier", ln=True, align="C")
    pdf.ln(10)

    # Date de génération
    pdf.set_font("Arial", size=10)
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pdf.cell(200, 10, txt=f"Date de génération : {current_date}", ln=True, align="R")
    pdf.ln(10)

    # Hypothèses de l'utilisateur
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Hypothèses retenues :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Valeur du bien : {property_value:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Taux d'intérêt : {interest_rate:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"- Durée du prêt : {years} ans", ln=True)
    pdf.cell(200, 10, txt=f"- Apport initial : {down_payment:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Frais de notaire retenus : {notary_fee_rate:.2f}%", ln=True)
    if current_net_income:
        pdf.cell(200, 10, txt=f"- Revenu net mensuel actuel : {current_net_income:.2f} EUR", ln=True)
    pdf.ln(10)

    # Résultats principaux
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Résultats principaux :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Frais de notaire : {notary_fees:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Coût total du projet : {project_cost:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Montant à emprunter : {loan_amount:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Mensualité : {monthly_payment:.2f} EUR", ln=True)
    if insurance_per_month:
        pdf.cell(200, 10, txt=f"- Assurance mensuelle : {insurance_per_month:.2f} EUR", ln=True)
    if existing_mortgage_payment:
        pdf.cell(200, 10, txt=f"- Crédit immobilier actuel : {existing_mortgage_payment:.2f} EUR / mois", ln=True)
    if rental_income:
        pdf.cell(200, 10, txt=f"- Revenu locatif estimé : {rental_income:.2f} EUR / mois", ln=True)
    pdf.cell(200, 10, txt=f"- Charge nette considérée : {combined_monthly_charge:.2f} EUR / mois", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Analyse d'acceptation bancaire :", ln=True)
    pdf.set_font("Arial", size=12)
    scenario_nette = ratio_scenarios["nette"]
    scenario_majoration = ratio_scenarios["majoration"]

    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Scénario 1 · Charge nette", ln=True)
    pdf.set_font("Arial", size=12)
    if scenario_nette["ratio"] is None:
        pdf.multi_cell(0, 10, txt="Revenu net mensuel non renseigné : impossible d'estimer le ratio d'endettement.")
    else:
        pdf.cell(200, 10, txt=f"- Ratio calculé : {scenario_nette['ratio']:.2%}", ln=True)
        pdf.cell(200, 10, txt=f"- Seuil cible : {debt_ratio:.0%}", ln=True)
        pdf.multi_cell(0, 10, txt=scenario_nette["message"])
    pdf.cell(200, 10, txt=f"- Mensualité projet (assurance incluse) : {monthly_payment:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Crédit immobilier en cours ajouté : {existing_mortgage_payment:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Revenu locatif déduit : {rental_income:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Charge nette utilisée : {combined_monthly_charge:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Revenu net mensuel déclaré : {current_net_income:.2f} EUR", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Scénario 2 · Revenu majoré", ln=True)
    pdf.set_font("Arial", size=12)
    adjusted_income = scenario_majoration["adjusted_income"]
    total_charge = scenario_majoration["total_charge"]
    ratio_majoration = scenario_majoration["ratio"]
    max_capacity = scenario_majoration["max_capacity"]
    haircut_display = scenario_majoration["haircut"] * 100

    pdf.cell(200, 10, txt=f"- Revenu retenu (incluant {haircut_display:.0f}% des loyers) : {adjusted_income:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Charges crédits (projet + existant) : {total_charge:.2f} EUR", ln=True)
    if ratio_majoration is not None:
        pdf.cell(200, 10, txt=f"- Ratio calculé : {ratio_majoration:.2%}", ln=True)
        pdf.cell(200, 10, txt=f"- Seuil cible : {debt_ratio:.0%}", ln=True)
    pdf.multi_cell(0, 10, txt=scenario_majoration["message"])
    pdf.cell(200, 10, txt=f"- Budget mensuel max pour le projet (après crédit en cours) : {max_capacity:.2f} EUR", ln=True)
    pdf.ln(5)

    # Revenus requis
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Revenus requis :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Revenu net mensuel requis : {(combined_monthly_charge / debt_ratio):.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Revenu brut mensuel requis : {(combined_monthly_charge / debt_ratio / net_to_gross_ratio):.2f} EUR", ln=True)
    pdf.ln(10)

    # Coût total du prêt
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Coût total du prêt :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Coût total du prêt (avec intérêts et assurance) : {total_paid:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Intérêts totaux sur la durée du prêt : {total_interest:.2f} EUR", ln=True)
    if insurance_per_month:
        pdf.cell(200, 10, txt=f"- Assurance totale : {total_insurance_cost:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Frais annexes : {total_ancillary_fees:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Coût global du projet financé : {grand_total_cost:.2f} EUR", ln=True)
    pdf.ln(10)

    # Retourne le PDF en tant que bytes
    return pdf.output(dest="S").encode("latin1")

# Validation des entrées utilisateur
st.sidebar.header("Paramètres")
interest_rate_input_mode = st.sidebar.radio(
    "Mode de saisie du taux d'intérêt",
    ["Curseur", "Saisie libre"],
    index=0,
)
if interest_rate_input_mode == "Curseur":
    interest_rate = st.sidebar.slider(
        "Taux d'intérêt (%)",
        min_value=0.5,
        max_value=10.0,
        value=3.50,
        step=0.1,
        format="%.2f",
    )
else:
    interest_rate = st.sidebar.number_input(
        "Taux d'intérêt (%)",
        min_value=0.50,
        max_value=20.00,
        value=3.50,
        step=0.01,
        format="%.2f",
    )
years = st.sidebar.slider("Durée (années)", min_value=5, max_value=30, value=25, step=1)
down_payment = st.sidebar.number_input("Apport initial (€)", min_value=0, value=0, step=1000)
property_value = st.sidebar.number_input("Valeur du bien (€)", min_value=100000, value=350000, step=10000)

# Choix du type de bien
property_type = st.sidebar.radio("Type de bien :", ["Ancien", "Neuf"])
notary_fee_rate = 7 if property_type == "Ancien" else 1

# Permettre à l'utilisateur de personnaliser les frais de notaire
notary_fee_rate = st.sidebar.slider(
    "Frais de notaire (%) [7% par défaut pour un bien ancien, 1% pour un bien neuf]",
    min_value=0.5,
    max_value=10.0,
    value=float(notary_fee_rate),
    step=0.1
)

# Ajout des seuils personnalisables
debt_ratio = st.sidebar.slider("Ratio d'endettement (33% par défaut)", min_value=0.1, max_value=0.5, value=0.33, step=0.01)
net_to_gross_ratio = st.sidebar.slider("Ratio net/brut (75% par défaut)", min_value=0.5, max_value=1.0, value=0.75, step=0.01)

# Assurance emprunteur
insurance_choice = st.sidebar.radio("Assurance emprunteur", ["Aucune", "Taux (%)", "Montant fixe (€)"], index=1)
if insurance_choice == "Taux (%)":
    insurance_rate = st.sidebar.number_input(
        "Taux d'assurance (%)",
        min_value=0.00,
        value=0.30,
        step=0.01,
        format="%.2f",
    )
    insurance_amount = 0.0
elif insurance_choice == "Montant fixe (€)":
    insurance_amount = st.sidebar.number_input("Montant assurance mensuel (€)", min_value=0.0, value=0.0, step=10.0)
    insurance_rate = 0.0
else:
    insurance_rate = 0.0
    insurance_amount = 0.0

# Situation financière actuelle
st.sidebar.markdown("### Situation financière actuelle")
has_existing_mortgage = st.sidebar.checkbox("Crédit immobilier en cours ?", value=True)
existing_mortgage_payment = 0.0
if has_existing_mortgage:
    existing_mortgage_payment = st.sidebar.number_input(
        "Mensualité du crédit en cours (€)",
        min_value=0.0,
        value=865.0,
        step=50.0,
    )

has_rental_income = st.sidebar.checkbox("Revenu locatif attendu ?", value=False)
rental_income = 0.0
if has_rental_income:
    rental_income = st.sidebar.number_input(
        "Revenu locatif mensuel (€)",
        min_value=0.0,
        value=0.0,
        step=50.0,
    )

current_net_income = st.sidebar.number_input(
    "Revenu net mensuel actuel (€)",
    min_value=0.0,
    value=6000.0,
    step=100.0,
)

# Validation pour éviter les incohérences
if property_value <= down_payment:
    st.error("L'apport initial ne peut pas être supérieur ou égal à la valeur du bien.")
    st.stop()

st.title("Simulateur de prêt immobilier")

# Affichage des onglets
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Rapport détaillé",
    "Capacité d'emprunt",
    "Revenu requis",
    "Tableau d'amortissement",
    "Analyse de sensibilité",
])

# Ajout du bouton de téléchargement dans le rapport détaillé
with tab1:
    st.subheader("Rapport détaillé")
    st.write("""
    Ce rapport fournit une vue d'ensemble détaillée des exigences de revenu, des mensualités, et du coût total du projet immobilier.
    """)
    generate_loan_report(
        property_value, interest_rate, years, down_payment, debt_ratio,
        net_to_gross_ratio, notary_fee_rate, insurance_choice, insurance_rate,
        insurance_amount, existing_mortgage_payment, rental_income, current_net_income
    )

    # Génération et téléchargement du PDF
    notary_fees = property_value * notary_fee_rate / 100
    project_cost = property_value + notary_fees
    loan_amount = project_cost - down_payment
    monthly_interest_rate = interest_rate / 100 / 12
    months = years * 12
    monthly_payment_bank = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** months) / \
                          ((1 + monthly_interest_rate) ** months - 1)
    if insurance_choice == "Taux (%)":
        insurance_per_month = loan_amount * insurance_rate / 100 / 12
    elif insurance_choice == "Montant fixe (€)":
        insurance_per_month = insurance_amount
    else:
        insurance_per_month = 0
    monthly_payment = monthly_payment_bank + insurance_per_month
    combined_monthly_charge = max(monthly_payment + existing_mortgage_payment - rental_income, 0)
    total_paid = monthly_payment * months
    total_interest = (monthly_payment_bank * months) - loan_amount
    total_insurance_cost = insurance_per_month * months
    total_ancillary_fees = notary_fees
    grand_total_cost = total_paid + total_ancillary_fees
    ratio_scenarios_pdf = compute_ratio_scenarios(
        monthly_payment,
        existing_mortgage_payment,
        rental_income,
        current_net_income,
        debt_ratio,
    )

    pdf_data = generate_pdf_report(
        property_value, interest_rate, years, down_payment, debt_ratio, net_to_gross_ratio, 
        notary_fee_rate, monthly_payment, loan_amount, total_paid, total_interest,
        notary_fees, project_cost, insurance_per_month, combined_monthly_charge,
        existing_mortgage_payment, rental_income, total_insurance_cost,
        total_ancillary_fees, grand_total_cost, current_net_income, ratio_scenarios_pdf
    )

    if loan_amount > 0:
        st.markdown("### Récapitulatif du coût global du financement")
        st.markdown(
            "\n".join(
                [
                    f"- **Montant total remboursé (capital + intérêts + assurance)** : {total_paid:,.2f} €",
                    f"- **Dont intérêts cumulés** : {total_interest:,.2f} €",
                    f"- **Dont assurance totale** : {total_insurance_cost:,.2f} €",
                    f"- **Frais annexes (notaire, etc.)** : {total_ancillary_fees:,.2f} €",
                    f"- **Coût global du projet financé** : {grand_total_cost:,.2f} €",
                ]
            )
        )

        st.markdown("### Sensibilité de la mensualité au taux d'intérêt")
        st.write(
            "Cette courbe illustre l'évolution de la mensualité totale (assurance incluse) pour un taux variant de 2% à 5% par pas de 0,1%. "
            "Le point rouge met en évidence la simulation actuelle."
        )

        interest_range = np.round(np.arange(2.0, 5.0 + 0.001, 0.1), 2)
        monthly_payments_vs_rate = []
        for rate in interest_range:
            monthly_rate = rate / 100 / 12
            payment_bank = loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
            monthly_payments_vs_rate.append(payment_bank + insurance_per_month)

        sensitivity_fig = go.Figure()
        sensitivity_fig.add_trace(
            go.Scatter(
                x=interest_range,
                y=monthly_payments_vs_rate,
                mode="lines",
                name="Mensualité totale",
            )
        )
        if interest_rate >= interest_range.min() and interest_rate <= interest_range.max():
            point_label = f"{interest_rate:.2f}% · {monthly_payment:,.2f} €"
            sensitivity_fig.add_trace(
                go.Scatter(
                    x=[interest_rate],
                    y=[monthly_payment],
                    mode="markers",
                    name=f"Simulation actuelle ({point_label})",
                    marker=dict(size=10, color="red"),
                )
            )
            sensitivity_fig.add_annotation(
                x=interest_rate,
                y=monthly_payment,
                text=point_label,
                showarrow=True,
                arrowhead=2,
                ax=40,
                ay=-40,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="red",
                borderwidth=1,
            )
        else:
            st.info("La simulation actuelle se situe en dehors de la plage 2% - 5% affichée.")

        sensitivity_fig.update_layout(
            xaxis_title="Taux d'intérêt (%)",
            yaxis_title="Mensualité totale (€)",
            hovermode="x unified",
            xaxis=dict(dtick=0.2, showgrid=True, gridcolor="rgba(200,200,200,0.5)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.3)"),
        )
        st.plotly_chart(sensitivity_fig, use_container_width=True)
    else:
        st.info("L'apport couvre entièrement le projet : aucune mensualité à visualiser.")

    # Bouton de téléchargement
    st.download_button(
        label="Télécharger le rapport en PDF 📄",
        data=pdf_data,
        file_name="rapport_pret_immobilier.pdf",
        mime="application/pdf",
    )
with tab2:
    st.subheader("Capacité d'emprunt")
    st.write("""
    Ce graphique montre comment la mensualité varie en fonction du montant du prêt demandé. 
    Vous pouvez ajuster le taux d'intérêt, la durée et l'apport initial pour voir l'impact sur les mensualités.
    """)
    st.markdown("### 💡 Simulation rapide de mensualité")

    selected_loan = st.slider(
        "Choisissez un montant de prêt pour simuler la mensualité associée :",
        min_value=150000,
        max_value=500000,
        step=10000,
        value=300000
    )

    loan_net = selected_loan - down_payment
    if loan_net <= 0:
        st.warning("L'apport couvre ou dépasse le montant du prêt sélectionné.")
    else:
        months = years * 12
        monthly_interest_rate = interest_rate / 100 / 12
        monthly_payment = loan_net * (monthly_interest_rate * (1 + monthly_interest_rate) ** months) / \
                          ((1 + monthly_interest_rate) ** months - 1)
        st.metric("Mensualité estimée", f"{monthly_payment:,.2f} €", help=f"Pour un emprunt de {selected_loan} €")
        
    st.pyplot(plot_borrowing_capacity(interest_rate, years, down_payment))

with tab3:
    st.subheader("Revenus requis")
    st.write("""
    Cet onglet vous permet de visualiser les revenus nécessaires pour couvrir différentes mensualités.
    Les mensualités sont ajustées en fonction des paramètres que vous avez définis.
    """)

    # Recalcul des mensualités en fonction du montant du prêt minimum et maximum
    loan_amounts = np.arange(150000, 500001, 10000)
    months = years * 12
    monthly_interest_rate = interest_rate / 100 / 12
    monthly_payments = [
        loan * (monthly_interest_rate * (1 + monthly_interest_rate) ** months) /
        ((1 + monthly_interest_rate) ** months - 1)
        for loan in loan_amounts
    ]

    # Calcul des revenus requis
    income_data = calculate_income_requirements(
        monthly_payments,
        debt_ratio,
        net_to_gross_ratio,
        existing_mortgage_payment,
        rental_income,
    )

    # Sélection du graphique
    option = st.radio(
        "Choisissez le type de revenu à visualiser :",
        ("Revenu net mensuel", "Revenu net annuel", "Revenu brut mensuel", "Revenu brut annuel")
    )

    # Génération des graphiques interactifs
    if option == "Revenu net mensuel":
        fig = px.line(
            x=loan_amounts, y=income_data['monthly_net'],
            labels={"x": "Montant du prêt (€)", "y": "Revenu net mensuel (€)"},
            title="Revenu net mensuel nécessaire pour chaque montant de prêt"
        )
        st.plotly_chart(fig, use_container_width=True)
    elif option == "Revenu net annuel":
        fig = px.line(
            x=loan_amounts, y=income_data['annual_net'],
            labels={"x": "Montant du prêt (€)", "y": "Revenu net annuel (€)"},
            title="Revenu net annuel nécessaire pour chaque montant de prêt"
        )
        st.plotly_chart(fig, use_container_width=True)
    elif option == "Revenu brut mensuel":
        fig = px.line(
            x=loan_amounts, y=income_data['monthly_gross'],
            labels={"x": "Montant du prêt (€)", "y": "Revenu brut mensuel (€)"},
            title="Revenu brut mensuel nécessaire pour chaque montant de prêt"
        )
        st.plotly_chart(fig, use_container_width=True)
    elif option == "Revenu brut annuel":
        fig = px.line(
            x=loan_amounts, y=income_data['annual_gross'],
            labels={"x": "Montant du prêt (€)", "y": "Revenu brut annuel (€)"},
            title="Revenu brut annuel nécessaire pour chaque montant de prêt"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tableau récapitulatif
    data = {
        "Mensualité (€)": monthly_payments,
        "Charge nette à couvrir (€)": income_data['adjusted_monthly_charge'],
        "Revenu net mensuel (€)": income_data['monthly_net'],
        "Revenu net annuel (€)": income_data['annual_net'],
        "Revenu brut mensuel (€)": income_data['monthly_gross'],
        "Revenu brut annuel (€)": income_data['annual_gross']
    }
    df = pd.DataFrame(data)

    st.write("### Tableau récapitulatif des revenus requis")
    st.dataframe(df.style.format({
        "Mensualité (€)": "{:.0f}",
        "Charge nette à couvrir (€)": "{:.0f}",
        "Revenu net mensuel (€)": "{:.2f}",
        "Revenu net annuel (€)": "{:.2f}",
        "Revenu brut mensuel (€)": "{:.2f}",
        "Revenu brut annuel (€)": "{:.2f}"
    }))

    # Bouton de téléchargement
    csv = convert_df_to_csv(df)
    st.download_button(
        label="Télécharger le tableau au format CSV",
        data=csv,
        file_name="revenus_requis.csv",
        mime='text/csv',
    )

with tab4:
    st.subheader("Tableau d'amortissement")
    amort_table = generate_amortization_schedule(loan_amount, interest_rate, years, insurance_per_month)
    st.dataframe(amort_table.style.format({
        "Mensualité": "{:.2f}",
        "Capital": "{:.2f}",
        "Intérêt": "{:.2f}",
        "Assurance": "{:.2f}",
        "Solde restant": "{:.2f}",
    }))
    csv_amort = convert_df_to_csv(amort_table)
    st.download_button(
        label="Télécharger l'amortissement CSV",
        data=csv_amort,
        file_name="amortissement.csv",
        mime='text/csv',
    )

    st.markdown("### Simulation de remboursement anticipé")
    extra_payment = st.number_input("Versement complémentaire mensuel (€)", min_value=0.0, value=0.0, step=100.0)
    start_month = st.number_input("Mois de début", min_value=1, value=1, step=1)
    if extra_payment > 0:
        new_schedule = simulate_prepayment(loan_amount, interest_rate, years, extra_payment, int(start_month), insurance_per_month)
        st.write(f"Durée restante : {len(new_schedule)} mois")
        st.dataframe(new_schedule.style.format({
            "Mensualité": "{:.2f}",
            "Capital": "{:.2f}",
            "Intérêt": "{:.2f}",
            "Assurance": "{:.2f}",
            "Solde restant": "{:.2f}",
        }))

with tab5:
    st.subheader("Analyse de sensibilité")
    st.write("""
    Explorez l'impact des variations de taux d'intérêt sur les mensualités.=:= 
    Ce graphique montre comment les mensualités évoluent en fonction des taux d'intérêt.
    """)

    start_rate = max(0.5, interest_rate - 1.0)
    end_rate = min(10.0, interest_rate + 1.0)
    interest_rate_range = np.arange(start_rate, end_rate + 0.01, 0.1)

    loan_amount = property_value + property_value * notary_fee_rate / 100 - down_payment
    months = years * 12

    data = []
    for rate in interest_rate_range:
        monthly_rate = rate / 100 / 12
        payment_bank = loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        monthly_payment = payment_bank + insurance_per_month
        total_cost = monthly_payment * months
        total_interest = (payment_bank * months) - loan_amount
        data.append({
            "Taux d'intérêt (%)": round(rate, 2),
            "Mensualité (€)": monthly_payment,
            "Coût total (€)": total_cost,
            "Intérêts totaux (€)": total_interest
        })

    df_sens = pd.DataFrame(data)
    st.dataframe(df_sens.style.format({
        "Taux d'intérêt (%)": "{:.2f}",
        "Mensualité (€)": "{:.2f}",
        "Coût total (€)": "{:.2f}",
        "Intérêts totaux (€)": "{:.2f}"
    }))

    fig = px.line(df_sens, x="Taux d'intérêt (%)", y="Mensualité (€)",
                  labels={"Taux d'intérêt (%)": "Taux d'intérêt (%)", "Mensualité (€)": "Mensualité (€)"},
                  title="Analyse de sensibilité des mensualités selon le taux d'intérêt")
    st.plotly_chart(fig, use_container_width=True)

    csv_sens = convert_df_to_csv(df_sens)
    st.download_button(
        label="Télécharger l'analyse CSV",
        data=csv_sens,
        file_name="analyse_sensibilite.csv",
        mime='text/csv'
    )
