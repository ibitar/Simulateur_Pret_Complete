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
import pandas as pd
from fpdf import FPDF
import tempfile
from datetime import datetime

# --- Pied de page / Informations version ---
st.sidebar.markdown("---")
st.sidebar.caption("🛠️ Développé par **I. Bitar**")
st.sidebar.caption("📅 Dernière mise à jour : **29 juin 2025**")
st.sidebar.caption("🔢 Version : **v1.1.0**")

st.markdown("---")
st.caption("🛠️ Développé par **I. Bitar** · 📅 Dernière mise à jour : **29 juin 2025** · 🔢 Version : **v1.1.0**")

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
def calculate_income_requirements(monthly_payments, debt_ratio, net_to_gross_ratio):
    required_monthly_net_incomes = [payment / debt_ratio for payment in monthly_payments]
    required_annual_net_incomes = [income * 12 for income in required_monthly_net_incomes]
    required_monthly_gross_incomes = [income / net_to_gross_ratio for income in required_monthly_net_incomes]
    required_annual_gross_incomes = [income * 12 for income in required_monthly_gross_incomes]

    return {
        "monthly_net": required_monthly_net_incomes,
        "annual_net": required_annual_net_incomes,
        "monthly_gross": required_monthly_gross_incomes,
        "annual_gross": required_annual_gross_incomes
    }

# Fonction pour générer le rapport de prêt
def generate_loan_report(property_value, interest_rate, years, down_payment, debt_ratio,
                         net_to_gross_ratio, notary_fee_rate, insurance_choice,
                         insurance_rate, insurance_amount):
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

    required_monthly_net_income = monthly_payment / debt_ratio
    required_annual_net_income = required_monthly_net_income * 12
    required_monthly_gross_income = required_monthly_net_income / net_to_gross_ratio
    required_annual_gross_income = required_annual_net_income / net_to_gross_ratio
    
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
    st.write(
        f"💡 La mensualité a été calculée sur la base d'un taux d'intérêt de **{interest_rate:.2f}%** et d'une durée de prêt de **{years} ans**."
    )

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
                        monthly_payment, loan_amount, total_paid, total_interest, notary_fees, project_cost, insurance_per_month):
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
    pdf.ln(10)

    # Revenus requis
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Revenus requis :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Revenu net mensuel requis : {(monthly_payment / debt_ratio):.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Revenu brut mensuel requis : {(monthly_payment / debt_ratio / net_to_gross_ratio):.2f} EUR", ln=True)
    pdf.ln(10)

    # Coût total du prêt
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Coût total du prêt :", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Coût total du prêt (avec intérêts) : {total_paid:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Intérêts totaux sur la durée du prêt : {total_interest:.2f} EUR", ln=True)
    pdf.ln(10)

    # Retourne le PDF en tant que bytes
    return pdf.output(dest="S").encode("latin1")

# Validation des entrées utilisateur
st.sidebar.header("Paramètres")
interest_rate = st.sidebar.slider("Taux d'intérêt (%)", min_value=0.5, max_value=10.0, value=3.1, step=0.1)
years = st.sidebar.slider("Durée (années)", min_value=5, max_value=30, value=25, step=1)
down_payment = st.sidebar.number_input("Apport initial (€)", min_value=0, value=0, step=1000)
property_value = st.sidebar.number_input("Valeur du bien (€)", min_value=100000, value=300000, step=10000)

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
insurance_choice = st.sidebar.radio("Assurance emprunteur", ["Aucune", "Taux (%)", "Montant fixe (€)"])
if insurance_choice == "Taux (%)":
    insurance_rate = st.sidebar.number_input("Taux d'assurance (%)", min_value=0.0, value=0.3, step=0.05)
    insurance_amount = 0.0
elif insurance_choice == "Montant fixe (€)":
    insurance_amount = st.sidebar.number_input("Montant assurance mensuel (€)", min_value=0.0, value=0.0, step=10.0)
    insurance_rate = 0.0
else:
    insurance_rate = 0.0
    insurance_amount = 0.0

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
        insurance_amount
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
    total_paid = monthly_payment * months
    total_interest = (monthly_payment_bank * months) - loan_amount

    pdf_data = generate_pdf_report(
        property_value, interest_rate, years, down_payment, debt_ratio, net_to_gross_ratio, 
        notary_fee_rate, monthly_payment, loan_amount, total_paid, total_interest,
        notary_fees, project_cost, insurance_per_month
    )

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
    income_data = calculate_income_requirements(monthly_payments, debt_ratio, net_to_gross_ratio)

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
        "Revenu net mensuel (€)": income_data['monthly_net'],
        "Revenu net annuel (€)": income_data['annual_net'],
        "Revenu brut mensuel (€)": income_data['monthly_gross'],
        "Revenu brut annuel (€)": income_data['annual_gross']
    }
    df = pd.DataFrame(data)

    st.write("### Tableau récapitulatif des revenus requis")
    st.dataframe(df.style.format({
        "Mensualité (€)": "{:.0f}",
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

    interest_rate_range = np.arange(2.0, 5.1, 0.5)
    sensitivity_data = {
        rate: [
            loan * ((rate / 100 / 12) * (1 + (rate / 100 / 12))**(years * 12)) /
            (((1 + (rate / 100 / 12))**(years * 12)) - 1)
            for loan in np.arange(150000, 500001, 10000)
        ]
        for rate in interest_rate_range
    }

    fig = px.line(
        x=interest_rate_range,
        y=[np.mean(values) for values in sensitivity_data.values()],
        labels={"x": "Taux d'intérêt (%)", "y": "Mensualité moyenne (€)"},
        title="Analyse de sensibilité des mensualités selon le taux d'intérêt"
    )
    st.plotly_chart(fig, use_container_width=True)
