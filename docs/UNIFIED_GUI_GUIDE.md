# Unified GUI Interface - Best of Both Worlds

The Unified GUI combines regular CES1 processing and universal sandbox mode in one seamless interface with proper background threading to prevent UI freezing.

## Key Features

### Fixed UI Freezing Issue
- Background Threading: Processing runs in separate threads
- Responsive Interface: GUI remains clickable during processing  
- Real-time Progress: Live updates without blocking
- Cancel Support: Stop processing at any time
- Status Updates: See exactly what's happening

### Tabbed Interface
- Regular Processing Tab: CES1-specific analysis
- Sandbox Mode Tab: Universal chromosome processing
- Shared Results: Common progress tracking and results display

### Enhanced User Experience
- Easy File Selection: Browse buttons for all file inputs
- Live Equation Testing: Test transformations before processing
- Real-time Progress: See processing status and completion percentage
- Detailed Results: Comprehensive success/error reporting
- Configuration Memory: Saves email and settings

## Launch Options

### **Default (Unified GUI)**
```bash
python main.py
# or
python unified_gui.py
```

### **Original Individual GUIs**
```bash
# Regular processing only
python gui.py

# Sandbox only  
python sandbox_gui.py

# Explicit unified
python main.py --unified
```

### **CLI Modes** (unchanged)
```bash
# Regular CLI
python cli.py --input_vcf file.vcf --output_dir ./out --type CES1P1-CES1 --email user@example.com

# Sandbox CLI
python sandbox_cli.py --input_vcf file.vcf --output_dir ./out --chromosome "16" --equation "x + 55758218" --email user@example.com
```

## 📋 **Interface Layout**

### Tab 1: Regular Processing (CES1)
```
File Selection
├── Input VCF File: [Browse]
└── Output Directory: [Browse]

CES1 Configuration  
├── Modification Type: [CES1P1-CES1 ▼]
└── Position Modifier: [55758218    ]

[Run Regular Processing]
```

### Tab 2: Sandbox Mode (Universal)
```
Configuration Sub-tab:
├── File Selection
│   ├── Input VCF File: [Browse]
│   └── Output Directory: [Browse]
├── Chromosome Configuration
│   ├── Target Chromosome: [16          ]
│   └── Output Format: [RefSeq ▼       ]  
└── Position Equation
    ├── Equation: [x + 55758218        ]
    └── Presets: [CES1] [Offset] [Scale]

Testing Sub-tab:
├── Test Positions: [100, 1000, 10000  ]
├── [Test Equation]
└── Results Table:
    │ Original │ Modified │
    │   100    │ 55758318 │
    │  1000    │ 55759218 │
    │ 10000    │ 55768218 │

[Run Sandbox Processing]
```

### Shared Bottom Section
```
Entrez API Configuration
└── Email: [your.email@example.com     ]

Processing Status  
├── Status: [Ready                     ]
└── Progress: [████████████     ] 75%

Processing Results
└── [Detailed results and file paths  ]

Controls: [Clear All] [Cancel Processing]
```

## Background Threading Architecture

### Problem Solved
Before: GUI froze during processing, couldn't click anything  
After: GUI remains fully responsive, can cancel or monitor progress

### Technical Implementation
```python
# Separate thread for each processing type
class RegularProcessingThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str) 
    processing_finished = pyqtSignal(dict)

class SandboxProcessingThread(QThread):
    # Same signals for consistency
```

### User Benefits
- Click anywhere during processing
- Switch tabs while processing  
- Cancel processing if needed
- Real-time updates on progress
- No more frozen interface

## Workflow Examples

### Regular CES1 Analysis
1. Select Tab: Click "Regular Processing (CES1)"
2. Choose Files: Browse for VCF and output directory
3. Configure: Select CES1P1-CES1 or CES1A2-CES1
4. Enter Email: Required for Entrez API
5. Run: Click "Run Regular Processing"
6. Monitor: Watch real-time progress and status
7. Results: View detailed results when complete

### Universal Sandbox Analysis
1. Select Tab: Click "Sandbox Mode (Universal)"
2. Configure: Set chromosome, equation, format
3. Test First: Use "Testing" sub-tab to validate equation
4. Choose Files: Browse for VCF and output directory  
5. Enter Email: Required for Entrez API
6. Run: Click "Run Sandbox Processing"
7. Monitor: Watch real-time progress and status
8. Results: View detailed results when complete

## Real-time Progress Features

### Status Updates
- "Ready" to "Starting processing..." to "Modifying VCF..." to "Annotating with rsIDs..." to "Completed"

### Progress Bar
- 0% to 10% to 25% to 75% to 100%
- Synchronized with actual processing steps

### Live Results
- Success: Shows summary statistics, file paths, completion details
- Errors: Shows error messages, completed steps, troubleshooting info

### Cancellation
- Cancel Button: Stops processing immediately
- Safe Cleanup: Properly terminates background threads
- Status Update: Shows "Processing cancelled by user"

## Advanced Features

### Configuration Memory
- Automatically saves and loads email address
- Remembers window size and position
- Preserves last used settings

### Input Validation
- Pre-processing: Validates all inputs before starting
- Real-time: Tests equations immediately  
- Clear Errors: Specific error messages with solutions

### File Management
- Smart Naming: Automatically generates organized output folders
- Path Display: Shows full paths to generated files
- Results Summary: Lists all created files with descriptions

## Troubleshooting

### GUI Won't Start
```bash
# Check PyQt6 installation
pip install PyQt6

# Try launching directly
python unified_gui.py
```

### Processing Stops Responding
- Fixed: Background threading prevents this
- Use "Cancel Processing" button if needed
- Check "Processing Results" for error details

### Email Configuration Issues
- Enter valid email in shared "Entrez API Configuration"  
- Email is automatically saved for future use
- Required for both regular and sandbox processing

## Migration Guide

### From Old GUI
- Same functionality, better experience
- All features preserved, just better organized
- Background processing prevents freezing
- Unified interface reduces window clutter

### Quick Start
```bash
# Old way (still works)
python gui.py
python sandbox_gui.py

# New way (recommended)  
python main.py
```

The Unified GUI gives you the best of both worlds - familiar CES1 processing and powerful sandbox mode - all in one responsive, professional interface.