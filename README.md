# rsID Retrieval

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Graphical User Interface (GUI)](#graphical-user-interface-gui)
  - [Command-Line Interface (CLI)](#command-line-interface-cli)
- [Parameters](#parameters)
- [Examples](#examples)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
## Overview

**rsID Retrieval** is a Python-based tool designed to process Variant Call Format (VCF) files by modifying positional information, cleaning data by removing columns that are deemed unnecessary by my team, annotating with rsIDs from the NCBI Entrez database, filtering significant entries, and generating comprehensive summary reports. It offers a user-friendly Graphical User Interface (GUI) built with PyQt6 and a versatile Command-Line Interface (CLI) for flexible usage scenarios.

## Features

- **VCF Modification:** Adjusts the `POS` field based on predefined criteria.
- **Data Cleaning:** Selects specific columns and standardizes chromosome identifiers.
- **rsID Annotation:** Fetches and annotates rsIDs using the NCBI Entrez API.
- **Filtering:** 
  - Retains only entries with valid rsIDs.
  - Filters entries based on quality scores.
- **Reporting:** Generates summary reports detailing the processing outcomes.
- **User Interfaces:**
  - **GUI:** Intuitive interface for users preferring graphical interactions.
  - **CLI:** Enables automation and integration into pipelines.
- **Progress Tracking:** Visual progress bar updates during processing.

## Installation

### Prerequisites
- **Python Version:** Python 3.7 or higher

### Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ayouballah/rsID_Retrieval.git
   cd rsID_Retrieval
   ```
2. **Create a Virtual Environment (Optional but Recommended):**
type the fellowing in your terminal:
```python
python -m venv venv
venv\Scripts\activate
