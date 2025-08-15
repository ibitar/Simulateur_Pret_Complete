import streamlit as st
import numpy as np
import pandas as pd
from fpdf import FPDF
import tempfile

# Configuration de la page
st.set_page_config(page_title="Valeur maximale du bien", layout="wide", initial_sidebar_state="expanded")

# --- Pied de page / Informations version ---
st.sidebar.markdown("---")
st.sidebar.caption("🛠️ Développé par **I. Bitar**")
st.sidebar.caption("📅 Dernière mise à jour : **15 août 2025**")
st.sidebar.caption("🔢 Version : **v1.2.0**")

st.markdown("---")
st.caption("🛠️ Développé par **I. Bitar** · 📅 Dernière mise à jour : **15 août 2025** · 🔢 Version : **v1.2.0**")

st.title("Valeur maximale du bien immobilier")

st.markdown(
    """
    Cette page estime la **valeur maximale du bien immobilier** que vous pouvez acheter
    en fonction d'une mensualité cible, d'une durée de prêt, d'un taux d'intérêt et d'un apport initial.
    Les frais de notaire sont estimés selon le type de bien :
    - **Neuf** : 2 % du prix du bien
    - **Ancien** : 7.5 % du prix du bien
    """
)

with st.form("max_property_form"):
    monthly_payment = st.number_input("Mensualité maximale souhaitée (€)", min_value=1.0, value=1500.0, step=50.0)
    years = st.number_input("Durée du prêt (années)", min_value=1, value=20, step=1)
    interest_rate = st.number_input("Taux d'intérêt (%)", min_value=0.0, value=3.0, step=0.1, format="%.2f")
    down_payment = st.number_input("Apport personnel (€)", min_value=0.0, value=30000.0, step=5000.0)
    property_type = st.radio("Type de bien", ["Neuf", "Ancien"], horizontal=True)
    submitted = st.form_submit_button("Calculer")

if submitted:
    notary_rates = {"Neuf": 2.0, "Ancien": 7.5}
    notary_rate = notary_rates[property_type]
    months = years * 12
    r = interest_rate / 100 / 12
    if r > 0:
        loan_amount = monthly_payment * ((1 + r) ** months - 1) / (r * (1 + r) ** months)
    else:
        loan_amount = monthly_payment * months
    property_value = (loan_amount + down_payment) / (1 + notary_rate / 100)
    notary_fees = property_value * notary_rate / 100
    project_cost = property_value + notary_fees

    st.subheader("Résultats")
    st.write(f"- **Valeur maximale du bien :** {property_value:,.2f} €")
    st.write(f"- **Frais de notaire ({notary_rate} %) :** {notary_fees:,.2f} €")
    st.write(f"- **Coût total du projet :** {project_cost:,.2f} €")
    st.write(f"- **Montant emprunté :** {loan_amount:,.2f} €")

    data = {
        "Élément": ["Valeur du bien", "Frais de notaire", "Apport", "Montant emprunté"],
        "Montant (€)": [property_value, notary_fees, down_payment, loan_amount],
    }
    df = pd.DataFrame(data)
    st.bar_chart(df.set_index("Élément"))
    st.dataframe(df.style.format({"Montant (€)": "{:.2f}"}))

    pdf = FPDF()
    if hasattr(pdf, "set_doc_option"):
        pdf.set_doc_option("core_fonts_encoding", "utf-8")
        euro_symbol = "€"
    else:
        euro_symbol = "EUR"
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Rapport de simulation", ln=True)
    pdf.cell(0, 10, f"Mensualité maximale : {monthly_payment:.2f} {euro_symbol}", ln=True)
    pdf.cell(0, 10, f"Durée du prêt : {years} ans", ln=True)
    pdf.cell(0, 10, f"Taux d'intérêt : {interest_rate:.2f} %", ln=True)
    pdf.cell(0, 10, f"Apport personnel : {down_payment:.2f} {euro_symbol}", ln=True)
    pdf.cell(0, 10, f"Type de bien : {property_type}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Valeur maximale du bien : {property_value:,.2f} {euro_symbol}", ln=True)
    pdf.cell(0, 10, f"Frais de notaire : {notary_fees:,.2f} {euro_symbol}", ln=True)
    pdf.cell(0, 10, f"Coût total du projet : {project_cost:,.2f} {euro_symbol}", ln=True)
    pdf.cell(0, 10, f"Montant emprunté : {loan_amount:,.2f} {euro_symbol}", ln=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp.seek(0)
        pdf_bytes = tmp.read()

    st.download_button(
        label="Télécharger le rapport PDF",
        data=pdf_bytes,
        file_name="valeur_bien_maximale.pdf",
        mime="application/pdf",
    )
