import streamlit as st
import pandas as pd
import nltk
import pdfplumber
from collections import Counter, defaultdict
import random
from io import BytesIO
from fpdf import FPDF

# Initialize NLTK
nltk.download('punkt')


# Load the CSV file with reference names and genders


def load_reference_csv(file):
    df = pd.read_csv(file, encoding='utf-8')

    # Identify name and gender columns
    name_column = None
    gender_column = None

    possible_name_columns = ['Name', 'name', 'firstName', 'firstname']
    possible_gender_columns = ['Gender', 'gender', 'sex']

    for col in possible_name_columns:
        if col in df.columns:
            name_column = col
            break

    for col in possible_gender_columns:
        if col in df.columns:
            gender_column = col
            break

    if not name_column or not gender_column:
        raise ValueError("CSV must contain name and gender columns.")

    # Create a name-gender dictionary
    name_gender_dict = dict(
        zip(df[name_column].str.lower(), df[gender_column].str.lower()))
    return name_gender_dict

# Extract text from PDF using pdfplumber


def extract_text_from_pdf(pdf_file):
    pdf_text = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                pdf_text.append(page.extract_text())
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return pdf_text

# Count genders in PDF text based on reference CSV


def count_genders_in_pdf(pdf_text, name_gender_dict):
    tokens = nltk.word_tokenize(pdf_text)
    names = [word for word in tokens if word.istitle() and word.lower()
             in name_gender_dict]
    genders = [name_gender_dict[name.lower()] for name in names]
    gender_count = Counter(genders)
    male_count = gender_count.get('m', 0)
    female_count = gender_count.get('f', 0)
    return male_count, female_count, names

# Modify text to balance gender mentions


def modify_gender_equality(pdf_text, names, name_gender_dict):
    gender_names = defaultdict(list)
    for name in names:
        gender = name_gender_dict[name.lower()]
        gender_names[gender].append(name)

    male_names = gender_names['m']
    female_names = gender_names['f']

    # Calculate the difference
    difference = abs(len(male_names) - len(female_names))

    # Determine the gender to replace
    if len(male_names) > len(female_names):
        replace_from, replace_to = 'm', 'f'
        names_to_replace = random.sample(male_names, difference)
    else:
        replace_from, replace_to = 'f', 'm'
        names_to_replace = random.sample(female_names, difference)

    # Get the list of possible replacement names
    possible_replacements = [
        name for name, gender in name_gender_dict.items() if gender == replace_to]

    # Replace names in the text
    modified_text = pdf_text
    for name in names_to_replace:
        replacement_name = random.choice(possible_replacements)
        modified_text = modified_text.replace(name, replacement_name, 1)

    return modified_text

# Save modified text to a new PDF


def save_text_to_pdf(text_list, output_stream):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("Arial", "", "", uni=True)  # Ensure UTF-8 support
    for text in text_list:
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, text)
    pdf.output(output_stream)

# Streamlit app


def main():
    st.title("Gender Balance in PDF Texts")

    uploaded_csv = st.file_uploader(
        "Upload CSV file with names and genders", type="csv")
    uploaded_pdf = st.file_uploader("Upload PDF file to analyze", type="pdf")

    if uploaded_csv and uploaded_pdf:
        try:
            name_gender_dict = load_reference_csv(uploaded_csv)
            pdf_pages_text = extract_text_from_pdf(uploaded_pdf)

            total_male_count = 0
            total_female_count = 0
            modified_total_male_count = 0
            modified_total_female_count = 0
            modified_texts = []

            for page_num, page_text in enumerate(pdf_pages_text, start=1):
                if page_text:  # Ensure the page_text is not None
                    male_count, female_count, names = count_genders_in_pdf(
                        page_text, name_gender_dict)
                    total_male_count += male_count
                    total_female_count += female_count

                    modified_text = modify_gender_equality(
                        page_text, names, name_gender_dict)
                    modified_male_count, modified_female_count, _ = count_genders_in_pdf(
                        modified_text, name_gender_dict)
                    modified_total_male_count += modified_male_count
                    modified_total_female_count += modified_female_count

                    st.write(
                        f"Page {page_num} - percentage of males mentioned: {male_count/(male_count+female_count)*100}")
                    st.write(
                        f"Page {page_num} - percentage of females mentioned: {female_count/(male_count+female_count)*100}")
                    st.write(
                        f"Page {page_num} - percentage of males mentioned after modification: {modified_male_count/(modified_female_count+modified_male_count)*100}")
                    st.write(
                        f"Page {page_num} - percentage of females mentioned after modification: {modified_female_count/(modified_female_count+modified_male_count)*100}")
                    st.write(
                        f"Page {page_num} - Modified text to balance gender mentions:")
                    st.write(modified_text)
                    st.write("\n" + "="*80 + "\n")

                    modified_texts.append(modified_text)

            st.write(
                f"percentage of males mentioned: {(total_male_count/(total_male_count+total_female_count)*100)}")
            st.write(
                f"percentage of females mentioned: {(total_female_count/(total_male_count+total_female_count)*100)}")
            st.write(
                f"percentage of males mentioned after modification: {(modified_total_male_count/(modified_total_female_count+modified_total_male_count)*100)}")
            st.write(
                f"percentage of females mentioned after modification: {(modified_total_female_count/(modified_total_male_count+modified_total_female_count)*100)}")

            if st.button("Download Modified PDF"):
                output = BytesIO()
                save_text_to_pdf(modified_texts, output)
                output.seek(0)
                st.download_button(label="Download Modified PDF", data=output,
                                   file_name="modified_pdf.pdf", mime="application/pdf")

        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
