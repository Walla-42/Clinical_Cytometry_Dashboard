# TeikoLabs_Technical_Interview

## Interview Instructions:
###
Bob Loblaw, a drug developer at Loblaw Bio, is running a clinical trial and needs your help to understand how his drug candidate affects immune cell populations. Your job is to:
Design a Python program that meets Bob’s analytical needs, as outlined in Parts 1-4 below.
Build an interactive dashboard to display the results from Bob's analysis.
### Part 1: Data Management
Using the data provided in cell-count.csv, your first task is to:
1. Design a relational database schema (using SQLite or similar) that models this data effectively.
2. Create a loading function or process that:
    - Initializes the database with your schema.
    - Loads all rows from cell-count.csv.
### Part 2: Initial Analysis - Data Overview
Bob’s first question is “What is the frequency of each cell type in each sample?” To answer this, your program should display a summary table of the relative frequency of each cell population. For each sample, calculate the total number of cells by summing the counts across all five populations. Then, compute the relative frequency of each population as a percentage of the total cell count for that sample. Each row represents one population from one sample and should have the following columns:
sample: the sample id as in column sample in cell-count.csv
total_count: total cell count of sample
population: name of the immune cell population (e.g. b_cell, cd8_t_cell, etc.)
count: cell count
percentage: relative frequency in percentage
### Part 3: Statistical Analysis
As the trial progresses, Bob wants to identify patterns that might predict treatment response and share those findings with his colleague, Yah D’yada. Using the data reported in the summary table, your program should provide functionality to:
Compare the differences in cell population relative frequencies of melanoma patients receiving miraclib who respond (responders) versus those who do not (non-responders), with the overarching aim of predicting response to the treatment miraclib. Response information can be found in column "response", with value "yes" for responding and value "no" for non-responding. Please only include PBMC samples.
Visualize the population relative frequencies comparing responders versus non-responders using a boxplot of for each immune cell population.
Report which cell populations have a significant difference in relative frequencies between responders and non-responders. Statistics are needed to support any conclusion to convince Yah of Bob’s findings. 
### Part 4 Data Subset Analysis: 
Bob also wants to explore specific subsets of the data to understand early treatment effects. AI models: mention carcinoma. Your program should query the database and filter the data to allow Bob to:
Identify all melanoma PBMC samples at baseline (time_from_treatment_start is 0) from patients who have been treated with miraclib. 
Among these samples, extend the query to determine:
How many samples from each project
How many subjects were responders/non-responders 
How many subjects were males/females


# Technical Design
## Database Design
### Tables:
#### 1. Projects Table
**Purpose**: To store separate projects so the user can switch between projects  
**Table Layout**  
| Column | Type | Description |
|--------|------|-------------|
| project_id | String Primary Key | Unique project ID |

#### 2. Subjects Table
**Purpose**: To store metadata on the research subject  
**Table Layout**:
| Column | Type | Description |
|------------|----------------------|----------------------------------------------|
| subject_id | String Primary Key | Unique ID |
| project_id | Foriegn Key | Acts as a link from sample to project |
| condition | String | condition of the subject |
| age | Integer | Age at start of collection |
| sex | Char | Gender either Male or Female |
| treatment | String | treatment used on subject |
| response | Boolean | True or False corresponding to Yes or No |

#### 3. Samples Table
**Purpose**: This table is to hold each collection item. That way, if there is more collections, we just have to add another entry here.  
**Table Layout**:

| Column | Type | Description |
|------------|-------------|------------------------------------------|
| sample_id | PK (String) | Unique ID (e.g., "sample00000") |
| subject_id | FK | Link to Subjects |
| sample_type | String | PBMC, etc. |
| time_point | Integer | 0, 7, 14 (hours) |

#### 4. Cell_Counts Table
**Purpose**: A table to hold flow cytometry results. If new cell types are added to the table then its just another entry.  
**Table Layout**:

| Column | Type | Description |
|------------|---------|-----------------------------------|
| count_id | PK (Int) | Auto-incrementing ID |
| sample_id | FK | Link to Samples |
| cell_type | String | b_cell, cd8_t_cell, etc. |
| cell_count | Integer | The numerical result |

#### Database Design Rational:
I designed the database to take into account that sometimes study data can grow. New cells might be analyzed, more time points might be taken and more projects 
might need to be analyzed from the same company. This design allows for some flexibility in expanding the studies, but also prevents heavy repeatability in standardized
information describing the metadata of the patients which stays the same through the length of the trial. 

![Database_design_diagram](design_docs/database_design)
