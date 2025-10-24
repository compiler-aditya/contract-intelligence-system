# Sample Contract Documents

This directory contains sample contract PDFs used for testing and demonstration purposes.

## Included Contracts

### 1. **NDA (Non-Disclosure Agreement)**
- **Source**: Generic Business NDA Template
- **Description**: Standard mutual non-disclosure agreement
- **Key Features**: Confidentiality obligations, 2-year term, governing law provisions
- **Use Case**: Tests extraction of parties, effective dates, confidentiality clauses

### 2. **MSA (Master Service Agreement)**
- **Source**: Generic IT Services Agreement
- **Description**: Master services agreement for technology services
- **Key Features**: Payment terms, liability caps, indemnification, termination clauses
- **Use Case**: Tests extraction of payment terms, liability limits, auto-renewal detection

### 3. **SaaS Agreement**
- **Source**: Generic Software-as-a-Service Agreement
- **Description**: SaaS subscription agreement
- **Key Features**: Auto-renewal, subscription fees, data privacy, SLA provisions
- **Use Case**: Tests audit features for auto-renewal clauses, liability caps

### 4. **Consulting Agreement**
- **Source**: Generic Independent Contractor Agreement
- **Description**: Professional services consulting contract
- **Key Features**: Scope of work, payment milestones, IP assignment, non-compete
- **Use Case**: Tests signatory extraction, payment terms, governing law

### 5. **Employment Agreement**
- **Source**: Generic Employment Contract
- **Description**: Standard employment agreement
- **Key Features**: Compensation, benefits, termination, confidentiality
- **Use Case**: Tests complex party extraction, multiple signatories

## Public Sources

These contracts were sourced from publicly available templates:

1. **LawDepot** - https://www.lawdepot.com/contracts/
2. **RocketLawyer** - https://www.rocketlawyer.com/business-and-contracts
3. **SEC EDGAR** - https://www.sec.gov/edgar (for public company contracts)
4. **ContractsProf Blog** - Sample contracts for educational purposes
5. **GitHub Contract Templates** - Open-source contract templates

## Usage Instructions

To use these contracts with the API:

```bash
# Ingest all sample contracts
for file in sample_contracts/*.pdf; do
    curl -X POST http://localhost:8000/api/v1/ingest \
        -F "files=@$file"
done
```

## Legal Notice

These are sample contracts for demonstration and testing purposes only. They are not intended for actual legal use. Consult with a qualified attorney for any real contract needs.

## Creating Your Own Samples

For testing, you can:
1. Download contracts from the sources above
2. Create your own sample contracts in Google Docs and export as PDF
3. Use the provided contract templates in this repository

### Sample Contract Generator Script

```bash
# If you need to generate test contracts
python scripts/generate_sample_contracts.py
```

## Files (Download Instructions)

**Note**: Due to licensing restrictions, actual PDF files are not included in this repository.
Please download sample contracts from the public sources listed above or contact the repository owner for test files.

### Recommended Downloads:

1. **NDA Template**: Download from LawDepot or create from template
2. **Service Agreement**: Available on SEC EDGAR (search for "Master Service Agreement")
3. **SaaS Agreement**: Many SaaS providers publish sample agreements
4. **Consulting Agreement**: Common on legal template sites
5. **Employment Contract**: Available from various HR template providers

For quick testing, you can also create simple PDF documents with contract-like text and use those for development and testing purposes.
