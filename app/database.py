import sqlite3
import pandas as pd
import logging
from logging.handlers import RotatingFileHandler
import functools

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=2)
file_handler.setLevel(logging.ERROR)
log_format = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
file_handler.setFormatter(log_format)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(log_format)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console)

class DataAccessError(Exception):
    """User-facing error indicating data could not be loaded."""
    DEFAULT_MSG = "Unable to load data at this time. Please try again later."

    def __init__(self, message=None, *, user_message=None, context=None):
        super().__init__(message or self.DEFAULT_MSG)
        self.user_message = user_message or self.DEFAULT_MSG
        self.context = context

def log_db_errors(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except DataAccessError:
            raise
        except sqlite3.Error as e:
            logger.exception("SQLite error in %s", func.__name__)
            try:
                self.conn.rollback()
            except Exception:
                logger.debug("Error: Unable to rollback database.")
            raise DataAccessError(context={"method": func.__name__}) from e
        except Exception as e:
            logger.exception("Unexpected error in %s", func.__name__)
            try:
                self.conn.rollback()
            except Exception:
                logger.debug("Error: Unable to rollback database.")
            raise DataAccessError(context={"method": func.__name__}) from e
    return wrapper

class Project_Database():
    def __init__(self, db_name="bobs_flow_project.db"):
        try:
            self.conn = sqlite3.connect(db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self._create_tables()
        except Exception as e:
            logger.exception("Failed to initialize database")
            raise DataAccessError(
                user_message="Unable to connect to the database.",
                context={"db_name": db_name}
            ) from e

    @log_db_errors
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
                            time_from_treatment_start REAL,
                            FOREIGN KEY (subject) REFERENCES subjects (subject)
                        )""")
        
        # Cell_Counts Table
        self.cursor.execute("""
                        CREATE TABLE IF NOT EXISTS cell_counts (
                            count_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sample TEXT,
                            population TEXT,
                            count INTEGER,
                            FOREIGN KEY (sample) REFERENCES samples (sample)
                        )""")


    @log_db_errors
    def load_csv_data(self, csv_file):
        """Takes a DataFrame and distributes it across the relational database tables.
        
        inputs:
            csv_data_filepath: the file path to the data in csv format

        outputs: 
            None
        """
        try:
            dataframe = pd.read_csv(csv_file)
            
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
        except (sqlite3.IntegrityError) as e:
            logger.exception("Error: User tried uploading duplicate data")
            raise DataAccessError(
                user_message="This data has already been loaded. Please upload new data.",
                context={"csv_file": str(csv_file)}
            ) from e
        
    @log_db_errors
    def get_conditions(self, project_id):
        self.cursor.execute(
            "SELECT DISTINCT condition FROM subjects WHERE project = ?", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    @log_db_errors
    def get_sample_types(self, project_id):
        self.cursor.execute(
            """SELECT DISTINCT sam.sample_type 
            FROM samples sam
            JOIN subjects sub ON sam.subject = sub.subject
            WHERE sub.project = ?""", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    @log_db_errors
    def get_time_points(self, project_id):
        self.cursor.execute(
            """SELECT DISTINCT sam.time_from_treatment_start 
            FROM samples sam
            JOIN subjects sub ON sam.subject = sub.subject
            WHERE sub.project = ?""", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    @log_db_errors
    def get_treatments(self, project_id):
        self.cursor.execute(
            "SELECT DISTINCT treatment FROM subjects WHERE project = ?", (project_id,)
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    @log_db_errors
    def get_projects(self):
        self.cursor.execute(
            "SELECT DISTINCT project FROM projects"
        )
        project_ids = [row[0] for row in self.cursor.fetchall()]
        return project_ids

    @log_db_errors
    def get_relative_frequencies(self, project_id):
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
            JOIN Totals t on c.sample = t.sample
            JOIN samples sam on c.sample = sam.sample
            JOIN subjects sub ON sam.subject = sub.subject
            WHERE sub.project = ?
            """

        self.cursor.execute(query, (project_id,))
        rows = self.cursor.fetchall()
        columns = ["sample", "total_count", "population", "count", "percentage"]
        
        data_dict = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        return pd.DataFrame(data_dict)

    @log_db_errors
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
        
        self.cursor.execute(query, (condition, sample_type, time_point, treatment))
        rows = self.cursor.fetchall()
        columns = ["response", "subject", "population", "percentage"]
        
        data_dict = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
        return pd.DataFrame(data_dict)

    def close_connection(self):
        logger.info("Closing database connection")
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                logger.warning("Failed to close database connection")


