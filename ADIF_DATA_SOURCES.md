# ADIF QSO Data Sources for AI/LLM Training

This document lists excellent sources for obtaining large ADIF QSO datasets to train the LLM AI model in W4GNS Logger AI.

## 📡 Public Amateur Radio Datasets

### 1. Club Log (Best for diversity)
- **URL**: https://clublog.org/
- **Features**: Millions of QSOs from thousands of operators worldwide
- **Access**: You can request bulk data exports or use their API
- **Pros**: Excellent geographic and temporal diversity

### 2. QRZ.com Logbook
- **URL**: https://logbook.qrz.com/
- **Features**: Large public logbook database
- **Access**: API available with subscription, some public logs downloadable
- **Pros**: Well-maintained, standardized data

### 3. LOTW (Logbook of The World)
- **URL**: https://lotw.arrl.org/
- **Features**: ARRL's massive QSO confirmation database
- **Access**: Request bulk data from ARRL for research purposes
- **Pros**: Highly verified, authoritative data

### 4. eQSL.cc
- **URL**: https://www.eqsl.cc/
- **Features**: Electronic QSL card system with millions of QSOs
- **Access**: Public logs available, bulk export possible
- **Pros**: Free access to large datasets

### 5. Contest Logs (Best for structured data)
- **CQ WW DX Contest**: https://www.cqww.com/publiclogs.htm
- **ARRL Contest Logs**: https://contests.arrl.org/
- **Features**: Thousands of contest logs with complete ADIF exports
- **Pros**: High-quality, complete data with consistent formatting

### 6. HamQTH.com
- **URL**: https://www.hamqth.com/
- **Features**: European-focused logbook service
- **Access**: API and exports available
- **Pros**: Good for European propagation patterns

### 7. POTA/SOTA Databases
- **POTA**: https://pota.app/
- **SOTA**: https://www.sotadata.org.uk/
- **Features**: Parks/Summits on the Air activations
- **Pros**: Excellent for portable operations and award tracking

## 🔬 Research Datasets

### 8. WSJT-X Spots Database
- **URL**: http://wsjt.sourceforge.net/
- **Features**: PSK Reporter data, FT8/FT4 spots
- **Pros**: Massive digital mode dataset, real-time propagation data

### 9. Reverse Beacon Network
- **URL**: http://reversebeacon.net/
- **Features**: Automated CW/digital skimming data
- **Pros**: High volume, automated, standardized

## 💡 Recommendations for W4GNS Logger AI

### Suggested Data Collection Approach:

1. **Start with Contest Logs (cleanest data)**
   - Download CQ WW, ARRL DX, Sweepstakes logs
   - Parse with the existing `load_adif()` function
   - Reason: Well-formatted, complete, and freely available

2. **Add POTA/SOTA data (award-specific)**
   - Direct API access available
   - Excellent for award recommendation training
   - Aligns with the awards tracking features

3. **Supplement with RBN/WSJT-X (propagation patterns)**
   - Real-time spot data
   - Great for band/mode/time recommendations

4. **Request bulk data for large-scale training**
   - Contact ARRL LOTW for research dataset
   - Request Club Log bulk export

## 📊 Data Processing Tips

### Example Implementation

```python
# filepath: w4gns_logger_ai/data_collection.py
"""Tools for collecting and preprocessing ADIF datasets for ML training."""

from pathlib import Path
from typing import List
import requests

from w4gns_logger_ai.adif import load_adif
from w4gns_logger_ai.models import QSO

def fetch_contest_logs(contest_url: str) -> List[QSO]:
    """Download contest logs in ADIF format.
    
    Args:
        contest_url: URL to ADIF file or contest log listing
        
    Returns:
        List of QSO objects parsed from the ADIF data
    """
    response = requests.get(contest_url, timeout=30)
    response.raise_for_status()
    return load_adif(response.text)

def fetch_pota_activations(park_id: str) -> List[QSO]:
    """Fetch POTA logs via API.
    
    Args:
        park_id: POTA park identifier (e.g., 'K-0001')
        
    Returns:
        List of QSO objects from POTA activations
    """
    api_url = f"https://api.pota.app/park/{park_id}"
    # Implement POTA API integration
    # TODO: Add proper API authentication and parsing
    pass

def preprocess_for_training(qsos: List[QSO]) -> dict:
    """Convert QSO data to ML training format.
    
    Args:
        qsos: List of QSO objects to process
        
    Returns:
        Dictionary with processed training data
    """
    return {
        "qso_patterns": [
            {
                "band": q.band,
                "mode": q.mode,
                "country": q.country,
                "grid": q.grid,
                "time": q.start_at.hour,
                "day_of_week": q.start_at.weekday(),
            }
            for q in qsos
        ]
    }

def download_contest_dataset(output_dir: Path) -> None:
    """Download a collection of contest logs for training.
    
    Args:
        output_dir: Directory to save downloaded ADIF files
    """
    contest_sources = [
        "https://www.cqww.com/publiclogs/2024_cw.htm",
        "https://www.cqww.com/publiclogs/2024_ssb.htm",
        # Add more contest log sources
    ]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for source in contest_sources:
        # Parse contest page and download individual logs
        # Save to output_dir
        pass
```

## 🎯 Best Starting Point

**Recommendation: Start with Contest Logs**

Contest logs are the best starting point because they are:
- ✅ Freely downloadable
- ✅ High quality and complete
- ✅ Well-formatted ADIF
- ✅ Large volume (10,000+ QSOs per log)
- ✅ Diverse operators and locations
- ✅ Timestamped accurately
- ✅ Include exchange data for awards

Then supplement with **POTA/SOTA** data since W4GNS Logger AI focuses on awards tracking.

## 🔗 Integration with W4GNS Logger AI

The collected datasets can be used to:

1. **Train award prediction models**
   - Learn patterns for DX, DXCC, WAS, VUCC
   - Identify optimal operating times/bands

2. **Improve AI recommendations**
   - Suggest bands/modes based on propagation patterns
   - Recommend contacts for specific awards

3. **Enhance the `ai_helper.py` module**
   - Better contextual suggestions
   - More accurate award progress predictions

4. **Validate awards calculations**
   - Test the `awards.py` module with real-world data
   - Ensure accuracy of award tracking

## 📝 Usage Example

```python
from pathlib import Path
from w4gns_logger_ai.data_collection import download_contest_dataset, preprocess_for_training
from w4gns_logger_ai.storage import add_qso

# Download training data
output_dir = Path("./training_data")
download_contest_dataset(output_dir)

# Import into database for analysis
for adif_file in output_dir.glob("*.adi"):
    qsos = load_adif(adif_file.read_text())
    for qso in qsos:
        add_qso(qso)

# Prepare for ML training
training_data = preprocess_for_training(qsos)
```

## 📚 Additional Resources

- **ADIF Specification**: http://adif.org/
- **Amateur Radio Data APIs**: https://github.com/topics/ham-radio
- **Propagation Data**: https://www.hamqsl.com/solar.html

---

*Last Updated: September 30, 2025*
