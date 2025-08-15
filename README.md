Voici une description détaillée du code pour un fichier README.md. Ce fichier explique les fonctionnalités, les dépendances, les instructions d’installation, et le fonctionnement de l’application Streamlit.

Simulateur de Prêt Immobilier (v1.2.0)

Dernière mise à jour : 15 août 2025

Cette application Streamlit permet de simuler un prêt immobilier en fonction de différents paramètres renseignés par l’utilisateur. Elle calcule et affiche des informations détaillées sur le prêt, notamment les mensualités, les revenus nécessaires, le coût total du prêt, et les intérêts cumulés. Un rapport PDF peut également être généré et téléchargé.

Fonctionnalités

1. Rapport détaillé
	•	Calcul des hypothèses basées sur les saisies de l’utilisateur, y compris :
	•	Valeur du bien.
	•	Taux d’intérêt.
	•	Durée du prêt.
	•	Apport initial.
	•	Frais de notaire (7% pour un bien ancien, 1% pour un bien neuf, ajustables).
	•	Calcul du montant emprunté, des mensualités, et des revenus nécessaires.
	•	Coût total du prêt (incluant les intérêts) et intérêts cumulés.
	•	Génération d’un rapport téléchargeable au format PDF avec :
	•	Les hypothèses retenues.
	•	Les résultats principaux.
	•	La date de génération.

2. Capacité d’emprunt
	•	Affichage d’un graphique montrant la relation entre le montant du prêt et les mensualités.
	•	Les paramètres ajustables incluent le taux d’intérêt, la durée du prêt, et l’apport initial.

3. Revenus requis
	•	Calcul et affichage des revenus nets et bruts nécessaires pour différentes mensualités.
	•	Graphiques interactifs (utilisant Plotly) permettant de visualiser :
	•	Revenu net mensuel et annuel requis.
	•	Revenu brut mensuel et annuel requis.
	•	Tableau récapitulatif téléchargeable au format CSV.

4. Tableau d'amortissement
        •       Génération d'un tableau mensuel indiquant la part de capital, d'intérêt et le solde restant.
        •       Téléchargement possible au format CSV.
        •       Simulation de remboursement anticipé grâce à des versements complémentaires.

5. Analyse de sensibilité
        •       Analyse de l’impact des variations du taux d’intérêt sur les mensualités moyennes.
        •       Graphique montrant les variations des mensualités en fonction des taux d’intérêt.

6. Valeur maximale du bien
        •       Estimation de la valeur maximale d'un bien achetable selon une mensualité cible, la durée du prêt, le taux d'intérêt et l'apport.
        •       Calcul automatique des frais de notaire et du montant emprunté.
        •       Génération d'un rapport PDF récapitulatif téléchargeable.

Installation

Prérequis
	•	Python 3.7 ou supérieur.
	•	Bibliothèques Python nécessaires :
	•	streamlit
	•	numpy
	•	matplotlib
	•	plotly
	•	pandas
	•	fpdf

Étapes d’installation
	1.	Clonez ce dépôt :

git clone https://github.com/votre-utilisateur/simulateur-pret-immobilier.git
cd simulateur-pret-immobilier


	2.	Installez les dépendances :

pip install -r requirements.txt


	3.	Lancez l’application :

streamlit run app.py

Paramètres utilisateur

Paramètres configurables dans la barre latérale
	•	Valeur du bien (€) : La valeur totale du bien immobilier.
	•	Taux d’intérêt (%) : Taux annuel appliqué au prêt (par défaut : 3.1%).
	•	Durée (années) : Nombre d’années pour rembourser le prêt (par défaut : 25 ans).
	•	Apport initial (€) : Montant que vous apportez (par défaut : 0 €).
	•	Type de bien : Choix entre un bien “Ancien” (7% frais de notaire par défaut) ou “Neuf” (1% frais de notaire par défaut).
	•	Frais de notaire (%) : Personnalisables entre 0.5% et 10%.
	•	Ratio d’endettement : Définit le pourcentage des revenus mensuels alloués au prêt (par défaut : 33%).
	•	Ratio net/brut : Définit la relation entre les revenus nets et bruts (par défaut : 75%).
        •       Assurance emprunteur configurable : taux (%) ou montant fixe.

Structure des onglets
	1.	Rapport détaillé
	•	Résumé des hypothèses et résultats principaux.
	•	Possibilité de télécharger un rapport au format PDF.
	2.	Capacité d’emprunt
	•	Graphique interactif montrant les mensualités en fonction du montant emprunté.
	3.	Revenus requis
	•	Graphiques et tableau récapitulatif des revenus nets et bruts requis.
	•	Possibilité de télécharger les données au format CSV.
	4.	Analyse de sensibilité
	•	Graphique montrant les variations des mensualités moyennes en fonction du taux d’intérêt.

Exemple d’utilisation
	1.	Lancez l’application Streamlit.
	2.	Configurez les paramètres dans la barre latérale :
	•	Entrez la valeur du bien, le taux d’intérêt, la durée du prêt, et l’apport initial.
	•	Sélectionnez le type de bien (Ancien/Neuf) et ajustez les frais de notaire si nécessaire.
	3.	Consultez les résultats dans les différents onglets :
	•	Visualisez le Rapport détaillé.
	•	Analysez les graphiques de Capacité d’emprunt et Revenus requis.
	•	Explorez l’Analyse de sensibilité pour différents taux d’intérêt.
	4.	Téléchargez le rapport détaillé en PDF ou le tableau des revenus en CSV.

Exemple de rapport PDF

Le rapport PDF inclut :
	•	Date de génération.
	•	Hypothèses retenues : Valeur du bien, apport, taux d’intérêt, durée, frais de notaire.
	•	Résultats principaux : Mensualités, montants empruntés, revenus requis.
	•	Coût total du prêt et intérêts cumulés.

Contributions

Les contributions sont les bienvenues ! Si vous souhaitez améliorer ce projet :
	1.	Forkez le dépôt.
	2.	Créez une branche de fonctionnalité :

git checkout -b feature-votre-fonctionnalite


	3.	Envoyez une pull request.

Licence

Ce projet est sous licence MIT. Consultez le fichier LICENSE pour plus d’informations.

Auteurs
	• Ibrahim BITAR - Créateur et développeur principal.

Testez le fichier et ajustez-le selon vos besoins ! 😊
