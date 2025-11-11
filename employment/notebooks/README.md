# Notebooks — employment


Purpose
- Collection of Jupyter notebooks that help discover job openings, extract job details, ingest your previous CV data, and generate customized CVs / application artifacts.



Recommended notebook order: 
1. notebooks/job_search_data/01_Search_jobs_lists_for_keywords.ipynb — crawl/parse job listing pages (e.g., LinkedIn, pharma companies). Uses requests/HTML parsing or a headless browser when required.
2. notebooks/job_search_data/02_fetch_job_details.ipynb — follow listing links and extract structured info.
3. notebooks/prepare_CV/01_Prepare_data_from_AwesomeCV.ipynb — load and normalize your existing CV/resume data from AwesomeCV ( https://github.com/posquit0/Awesome-CV ) .
4. notebooks/prepare_CV/02_Prepare_CV_for_jobs_toapply.ipynb — match job requirements to your CV content, score & rank previous documents by provided job fit. TODO: Improve prompt by adding instructions per entry. 
5. Generate cv with AwesomeCV ( https://github.com/posquit0/Awesome-CV ) , produce outputs (PDF).
5. TODO — example end-to-end pipeline: scrape → fetch → match → generate.



Structures after every step: 
01: 
```
(base) Kostass-MacBook-Pro:examples kbillis$ ls -l ./Bioinformatics_2025_09*
./Bioinformatics_2025_09:
total 64
-rw-r--r--  1 kbillis  staff  1772 27 Oct 08:14 additional_info.tex
-rw-r--r--  1 kbillis  staff  2561 13 Oct 22:25 education.tex
-rw-r--r--  1 kbillis  staff  6348 27 Oct 08:15 experience_bioinformatics.tex
-rw-r--r--  1 kbillis  staff  2823 27 Oct 08:16 key_skills.tex
-rw-r--r--@ 1 kbillis  staff  4941 26 Sep 12:04 resume_konstantinos_billis_25_08_Bioinformatics.tex
-rw-r--r--  1 kbillis  staff  1340 26 Sep 12:17 summary_bioinformatics.tex

./Bioinformatics_2025_09_biomarkers:
total 64
-rw-r--r--  1 kbillis  staff  1768 23 Aug 21:59 additional_info.tex
-rw-r--r--  1 kbillis  staff  2470 10 Sep 09:57 education.tex
-rw-r--r--  1 kbillis  staff  5967 11 Sep 10:44 experience_bioinformatics.tex
-rw-r--r--  1 kbillis  staff  2761 10 Sep 10:01 key_skills.tex
-rw-r--r--  1 kbillis  staff  4997 10 Sep 10:03 resume_konstantinos_billis_25_09_Biomarkers.tex
-rw-r--r--  1 kbillis  staff  1156 10 Sep 10:10 summary_bioinformatics.tex

./Bioinformatics_2025_09_cancer:
total 64
-rw-r--r--  1 kbillis  staff  1786 11 Sep 11:25 additional_info.tex
-rw-r--r--  1 kbillis  staff  2471 11 Sep 11:26 education.tex
-rw-r--r--  1 kbillis  staff  5354 12 Sep 11:17 experience_bioinformatics.tex
-rw-r--r--  1 kbillis  staff  2612 12 Sep 11:18 key_skills.tex
-rw-r--r--  1 kbillis  staff  4977 11 Sep 11:11 resume_konstantinos_billis_25_09_Biomarkers.tex
-rw-r--r--  1 kbillis  staff  1156 11 Sep 11:11 summary_bioinformatics.tex
```

02: 
```
organized_files/
├── additional_info/
│   └── (Contains 13 files)
├── education/
│   └── (Contains 17 files)
├── experience/
│   └── (Contains 48 files)
├── key_skills/
│   └── (Contains 58 files)
├── summary/
│   └── (Contains 46 files)
├── file_mappings.json
└── ORGANIZATION_REPORT.md
``` 




Dependencies: 
- Python 3.13.9
- Typical libraries: requests, beautifulsoup4, ... 
- Install example:
    - pip install -r requirements.txt



Usage notes
- Run notebooks in the listed order for an end-to-end flow.
- Use the pipeline notebook to automate repeated runs.
- Store credentials and sensitive tokens in .env (do not commit them).
- Good luck!! 
