# School Holidays & Term Dates Extractor  

This project automates the extraction of official school holiday and term date information from district or LEA websites. It supports CSV inputs for both **USA** and **UK** schools and outputs normalized JSON files.  

---

##  Setup  

1. **Clone the repository** and open a terminal in the project directory.  

2. **Install dependencies**:  
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**:  
   ```bash
   playwright install
   ```

4. **Configure environment variables**:  
   Create a `.env` file in the project root with the following keys:  

   ```env
   BRIGHTDATA_SERP_KEY="your key"
   PERPLEXITY_KEY="your key"
   GEMINI_KEY="your key"
   PROXY_HOST=brd.superproxy.io
   PROXY_PORT=33335
   PROXY_USERNAME="your key"
   PROXY_PASSWORD="your key"
   ```

   ###  Key descriptions
   - **BRIGHTDATA_SERP_KEY ** – API keys for [Bright Data SERP](https://brightdata.com/) search scraping.  
   - **PERPLEXITY_KEY** – API key for [Perplexity AI](https://perplexity.ai/) integration.  
   - **GEMINI_KEY** – API key for [Google Gemini](https://ai.google.dev/) model access.  
   - **PROXY_HOST, PROXY_PORT, PROXY_USERNAME, PROXY_PASSWORD** – Residential proxy configuration from Bright Data.  

---

## Input  

Navigate to the `input` folder and place your CSV files there. Two formats are supported:  

- **USA schools** (must have these columns):  
  ```
  COUNTRY,STATENAME,LEA_NAME,REGION_CITY,WEBSITE
  ```

- **UK schools** (must have these columns):  
  ```
  Country,Region,LEA,Holiday URL
  ```

---

##  Running  

From the project root, run:  

```bash
python run.py
```

The script will:  
- Process each CSV file in the `input` folder.  
- Extract official holiday and term date information.  
- Save results in JSON format in an auto-generated `output` folder.  
- Generate detailed logs in a `logs` folder (new log file for each run).  

---

## Output  

- **Output folder**: Contains JSON files with normalized holiday/term data.  
- **Logs folder**: Contains run-specific log files for debugging and traceability.  

---

##  Third-Party Services Required  

This project requires access to several third-party APIs and services:  
- [Bright Data SERP](https://brightdata.com/) – to fetch search results.  
- [Perplexity AI](https://perplexity.ai/) – to enhance information retrieval.  
- [Google Gemini](https://ai.google.dev/) – for large language model processing.  
- [Bright Data Proxies](https://brightdata.com/proxy-residential) – to ensure reliable scraping.  
