import sqlite3
import pandas as pd

class Project_Database():
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
                            project STRING PRIMARY KEY
                        )""")
        
        # Subjects Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS subjects (
                            subject TEXT PRIMARY KEY,
                            project TEXT,
                            condition TEXT,
                            age INTEGER,
                            sex CHAR,
                            treatment TEXT,
                            response INTEGER,
                            FOREIGN KEY (project) REFERENCES projects (project)
                        )""")
        
        # Samples Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS samples (
                            sample TEXT PRIMARY KEY,
                            subject TEXT,
                            sample_type TEXT,
                            time_from_treatment_start INTEGER,
                            FOREIGN KEY (subject) REFERENCES subjects (subject)
                        )""")
        
        # Cell_Counts Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS cell_counts (
                            count_id INTEGER PRIMARY KEY,
                            sample TEXT,
                            population TEXT,
                            count INTEGER,
                            FOREIGN KEY (sample) REFERENCES samples (sample)
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
        subjects.to_sql('subjects', self.conn, if_exists='append', index=False)

        samples = dataframe[['sample', 'subject', 'sample_type', 'time_from_treatment_start']].drop_duplicates()
        samples.to_sql('samples', self.conn, if_exists='append', index=False)

        cell_cols = ['b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']
        insert_data = [
            (row['sample'], population, row[population])
            for _, row in dataframe.iterrows()
            for population in cell_cols
        ]
        self.cursor.executemany(
            "INSERT INTO cell_counts (sample, population, count) VALUES (?, ?, ?)",
            insert_data
        )
        self.conn.commit()

    def get_conditions(self, project_id):
        self.cursor.execute(
            "SELECT DISTINCT condition FROM subjects WHERE project = ?", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_sample_types(self, project_id):
        self.cursor.execute(
            """SELECT DISTINCT sam.sample_type 
            FROM samples sam
            JOIN subjects sub ON sam.subject = sub.subject
            WHERE sub.project = ?""", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_time_points(self, project_id):
        self.cursor.execute(
            """SELECT DISTINCT sam.time_from_treatment_start 
            FROM samples sam
            JOIN subjects sub ON sam.subject = sub.subject
            WHERE sub.project = ?""", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_treatments(self, project_id):
        self.cursor.execute(
            "SELECT DISTINCT treatment FROM subjects WHERE project = ?", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_projects(self):
        self.cursor.execute(
            "SELECT DISTINCT project FROM projects"
        )
        project_ids = [row[0] for row in self.cursor.fetchall()]
        return project_ids

    def get_relative_frequencies(self):
        """A method that calculates relative frequencies for all samples
        
        input:
            None

        output:
            relative_frequency: The relative frequencies for all cells within a sample calculated as the number of cells of a given 
                cell type divided by the total count of cells for a specific sample multiplied by 100 and presented as a percentage.

        """
        query = """
            WITH Totals AS (
                SELECT sample, SUM(count) as total_count
                FROM cell_counts
                GROUP BY sample
            )
            SELECT 
                c.sample, 
                t.total_count, 
                c.population, 
                c.count,
                (CAST(c.count AS FLOAT) / t.total_count) * 100 AS percentage
            FROM cell_counts c
            JOIN Totals t ON c.sample = t.sample
        """

        relative_frequency = pd.read_sql(query, self.conn)
        return relative_frequency

    def get_statistical_subset(self, condition, sample_type, time_point, treatment):
        """A method that filters data for responder vs non-responder analysis

        inputs:
            condition:
            sample_type: 

        outputs:
            sample_subset: The subset from the selected condition and sample types for the given study
        """

        query = f"""
            SELECT sub.response, sub.subject, c.population, 
                (CAST(c.count AS FLOAT) / t.total_count) * 100 AS percentage
            FROM subjects sub
            JOIN samples sam ON sub.subject = sam.subject
            JOIN cell_counts c ON sam.sample = c.sample
            JOIN (SELECT sample, SUM(count) as total_count FROM cell_counts GROUP BY sample) t 
                ON c.sample = t.sample
            WHERE sub.condition = ? 
            AND sam.sample_type = ?
            AND sam.time_from_treatment_start = ?
            AND sub.treatment = ?
        """
        
        sample_subset = pd.read_sql(query, self.conn, params=[condition, sample_type, time_point, treatment])
        return sample_subset

    def close_connection(self):
        self.conn.close()


