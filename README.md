# rsID Retrieval
> The Docker link is underwork (I need to adjust the packages that support the GUI implementation) same for the VM
> The current workaround revolves around pulling the Github repo and using it directly
## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Graphical User Interface (GUI)](#graphical-user-interface-gui)
  - [Command-Line Interface (CLI)](#command-line-interface-cli)
  - [through docker](#through-docker)
- [Parameters](#parameters)
- [Examples](#example)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
## Overview
**rsID Retrieval** is a Python-based tool designed for targeted sequencing analysis, specifically processing Variant Call Format (VCF) files obtained from nanopore sequencing of chromosome 16. It modifies positional information, removes unnecessary columns, and annotates variants with rsIDs from the NCBI variations and Entrez database. The tool is particularly helpful for targeted reads studies, enabling  the identification of synonymous variants. It also filters significant entries and generates comprehensive summary reports. With a user-friendly Graphical User Interface (GUI) built with PyQt6 and a versatile Command-Line Interface (CLI), it offers flexible usability for diverse research needs.

## Features

- **VCF Modification:** Adjusts the `POS` field based on predefined criteria.
- **Data Cleaning:** Selects specific columns and standardizes chromosome identifiers.
- **rsID Annotation:** Fetches and annotates rsIDs using the NCBI Entrez API.
- **Filtering:** 
  - Retains only entries with valid rsIDs.
  - Filters entries based on quality scores.
- **Reporting:** Generates summary report detailing the processing outcomes and multiple vcf files with different types of outcomes 
- **User Interfaces:**
  - **GUI:** Intuitive interface for users preferring graphical interactions.
  - **CLI:** Enables automation and integration into pipelines.
- **Progress Tracking:** Visual progress bar updates during processing.

## Installation

### Prerequisites
- **Python Version:** This tool has been tested and developed under Python version 3.12.3 

### Steps
#### I. through GitHub
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ayouballah/rsID_Retrieval.git 
   cd rsID_Retrieval 
   ```
2. **Create a Virtual Environment (Optional but Recommended):**
type the following in your terminal:
```python
python -m venv venv
venv\Scripts\activate # If you're using Windows, for Unix systems please use (source venv/bin/activate)
```
3. proceed by **installing the dependencies**
```Python
pip install -r requirements.txt
```
#### II. through Docker Hub

1. For convenience, a pre-built Docker image is available. You can pull and run it without needing to build it manually.
please run the fellowing command after making sure you're logged in your docker Hub account 
```
docker pull ayouballah/rsid_retrieval:v1.0
```

## Usage   
depending on the approach followed and the desired user interface the usage will be slightly different:

if you Cloned the repository you have two main approaching:

### graphical-user-interface-gui
1. Run the Application:
```python
python rsID_retrieval.py
```
2. provide the details:
- Browse and select the input VCF file.
- Specify the output directory.
- Enter your email (required by Entrez).
- Choose the modification type.
- Set the position modifier (if applicable).
- Click "Run" to start the process.
the command used will be available shorty afterwards

alternitivly you can run it through the command line :
### command-line-interface-cli
1. Run the Application with Required Arguments:
```python
python rsID_retrieval.py --input_vcf "path_to_input_vcf" --output_dir "path_to_output_dir" --email "your_email" --type modification_type --pos_modifier value
```

### through-docker 
if you used the docker hub:

```bash
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/results:/app/results rsid_retrieval --input_vcf "data/input.vcf" --output_dir "results" --email "your_email@example.com" --type CES1P1/CES1A2-CES1 --pos_modifier 55758218
```
### Parameters
--help/h: provides a short explination on how to use the tool.
--input_vcf: Path to the input VCF file.
--output_dir: Path to save the final annotated VCF files.
--email: Email required by Entrez to initialize the search process.
--type: Type of position modification (CES1P1-CES1 or CES1A2-CES1).
--pos_modifier: Value to add to each POS entry (only for CES1P1-CES1).

### example
```python
C:/Users/ayoub/anaconda3/python.exe "C:.....path/RSIDs_recover.py"--input_vcf "c:...../S8 Ces1p1 Ces1.vcf" --output_dir "c:..../stuff" --type CES1P1-CES1 --email "gmail.com" --pos_modifier 55758218
```
### Dependencies
rsID_retrieval relies on a few robustly maintained third party libraries listed below. The correct versions of the packages are installed together with the software when using pip.
- pandas==2.2.2
- requests==2.32.2
- PyQt6==6.7.0
- biopython==1.84
- tqdm==4.66.4
### Configuration
The tool uses a configuration file (config.json) to store the user's email for Entrez API access.


### troubleshooting 
If you encounter any issues, please check the following:
Ensure all dependencies are installed.
Verify the input VCF file format.
Check your internet connection for Entrez API access.


### contributing 
Contributions are welcome! writing issue is will provide me a great deal of help improving it and you're more than welcome to fork the project and work on it yourself !!


### License
This project is licensed under the MIT License. See the LICENSE file for details.
