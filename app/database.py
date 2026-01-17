import sqlite3
import pandas as pd

class Project_Databae():
    def __init__(self, db_name="bobs_flow_project.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """A function to initalize the relational database
        
        Tables:
            projects: 
            subjects:
            samples:
            cell_counts:
            
        """

        # Projects Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS projects (
                            project_id STRING PRIMARY KEY
                        )""")
        
        # Subjects Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS subjects (
                            subject_id TEXT PRIMARY KEY,
                            project_id TEXT,
                            condition TEXT,
                            age INTEGER,
                            sex CHAR,
                            treatment TEXT,
                            response INTEGER,
                            FOREIGN KEY (project_id) REFERENCES projects (project_id)
                        )""")
        
        # Samples Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS samples (
                            sample_id TEXT PRIMARY KEY,
                            subject_id TEXT,
                            sample_type TEXT,
                            time_point INTEGER,
                            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
                        )""")
        
        # Cell_Counts Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS cell_counts (
                            count_id INTEGER PRIMARY KEY,
                            sample_id TEXT,
                            cell_type TEXT,
                            cell_count INTEGER,
                            FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
                        )""")
    
    def load_csv_data(self, csv_data_filepath):
        """Takes a DataFrame and distributes it across the relational database tables.
        
        inputs:
            csv_data_filepath: the file path to the data in csv format

        outputs: 
            None
        """

        dataframe = pd.read_csv(csv_data_filepath)
        
        projects = dataframe[['project']].drop_duplicates()
        projects.to_sql('projects', self.conn, if_exists='append', index=False)

        subjects = dataframe[['subject', 'project', 'condition', 'age', 'sex', 'treatment', 'response']].drop_duplicates()
        subjects.columns = ['subject_id', 'project_id', 'condition', 'age', 'sex', 'treatment', 'response']
        subjects.to_sql('subjects', self.conn, if_exists='append', index=False)

        samples = dataframe[['sample', 'subject', 'sample_type', 'time_from_treatment_start']].drop_duplicates()
        samples.columns = ['sample_id', 'subject_id', 'sample_type', 'time_point']
        samples.to_sql('samples', self.conn, if_exists='append', index=False)

        cell_cols = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']
        insert_data = [
            (row['sample'], cell_type, row[cell_type])
            for _, row in dataframe.iterrows()
            for cell_type in cell_cols
        ]
        self.cursor.executemany(
            "INSERT INTO cell_counts (sample_id, cell_type, cell_count) VALUES (?, ?, ?)",
            insert_data
        )
        self.conn.commit()

    def close_connection(self):
        self.conn.close()


