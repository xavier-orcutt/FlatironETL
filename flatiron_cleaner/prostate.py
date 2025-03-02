import pandas as pd
import numpy as np
import logging
import math 
import re 
from typing import Optional

logging.basicConfig(
    level = logging.INFO,                                 
    format = '%(asctime)s - %(levelname)s - %(message)s'  
)

class DataProcessorProstate:

    GROUP_STAGE_MAPPING = {        
        # Stage IV
        'IV': 'IV',
        'IVA': 'IV',
        'IVB': 'IV',

        # Stage III
        'III': 'III',
        'IIIA': 'III',
        'IIIB': 'III',
        'IIIC': 'III',

        # Stage II
        'II': 'II',
        'IIA': 'II',
        'IIB': 'II',
        'IIC': 'II',

        # Stage I
        'I': 'I',
        
        # Unknown
        'Unknown / Not documented': 'unknown'
    }

    T_STAGE_MAPPING = {
        'T4': 'T4',
        'T3': 'T3',
        'T3a': 'T3',
        'T3b': 'T3',
        'T2': 'T2',
        'T2a': 'T2',
        'T2b': 'T2',
        'T2c': 'T2',
        'T1': 'T1',
        'T1a': 'T1',
        'T1b': 'T1',
        'T1c': 'T1',
        'T0': 'T1',
        'TX': 'unknown',
        'Unknown / Not documented': 'unknown'
    }

    N_STAGE_MAPPING = {
        'N1': 'N1',
        'N0': 'N0',
        'NX': 'unknown',
        'Unknown / Not documented': 'unknown'
    }

    M_STAGE_MAPPING = {
        'M1': 'M1',
        'M1a': 'M1',
        'M1b': 'M1',
        'M1c': 'M1',
        'M0': 'M0',
        'Unknown / Not documented': 'unknown'
    }

    GLEASON_MAPPING = {
        '10': 5,
        '9': 5,
        '8': 4,  
        '4 + 3 = 7': 3,
        '7 (when breakdown not available)': 3,
        '3 + 4 = 7': 2, 
        'Less than or equal to 6': 1,  
        'Unknown / Not documented': 'unknown'
    }

    STATE_REGIONS_MAPPING = {
        'ME': 'northeast', 
        'NH': 'northeast',
        'VT': 'northeast', 
        'MA': 'northeast',
        'CT': 'northeast',
        'RI': 'northeast',  
        'NY': 'northeast', 
        'NJ': 'northeast', 
        'PA': 'northeast', 
        'IL': 'midwest', 
        'IN': 'midwest', 
        'MI': 'midwest', 
        'OH': 'midwest', 
        'WI': 'midwest',
        'IA': 'midwest',
        'KS': 'midwest',
        'MN': 'midwest',
        'MO': 'midwest', 
        'NE': 'midwest',
        'ND': 'midwest',
        'SD': 'midwest',
        'DE': 'south',
        'FL': 'south',
        'GA': 'south',
        'MD': 'south',
        'NC': 'south', 
        'SC': 'south',
        'VA': 'south',
        'DC': 'south',
        'WV': 'south',
        'AL': 'south',
        'KY': 'south',
        'MS': 'south',
        'TN': 'south',
        'AR': 'south',
        'LA': 'south',
        'OK': 'south',
        'TX': 'south',
        'AZ': 'west',
        'CO': 'west',
        'ID': 'west',
        'MT': 'west',
        'NV': 'west',
        'NM': 'west',
        'UT': 'west',
        'WY': 'west',
        'AK': 'west',
        'CA': 'west',
        'HI': 'west',
        'OR': 'west',
        'WA': 'west',
        'PR': 'unknown'
    }

    def __init__(self):
        self.enhanced_df = None
        self.demographics_df = None
        self.practice_df = None 
        self.biomarkers_df = None
        self.vitals_df = None 

    def process_enhanced(self,
                         file_path: str,
                         index_date_column: str = 'MetDiagnosisDate',
                         patient_ids: list = None,
                         index_date_df: pd.DataFrame = None,
                         drop_stages: bool = True,
                         drop_dates: bool = True) -> pd.DataFrame: 
        """
        Processes Enhanced_MetProstate.csv to standardize categories, consolidate staging information, and calculate time-based metrics between key clinical events.
        
        The index date is used to determine castrate-resistance status by that time and to calculate time from diagnosis to castrate resistance. 
        The default index date is 'MetDiagnosisDate.' For an alternative index date, provide an index_date_df and specify the index_date_column accordingly.
        
        To process only specific patients, either:
        1. Provide patient_ids when using the default index date ('MetDiagnosisDate')
        2. Include only the desired PatientIDs in index_date_df when using a custom index date
        
        Parameters
        ----------
        file_path : str
            Path to Enhanced_MetProstate.csv file
        index_date_column : str, default = 'MetDiagnosisDate'
            name of column for index date of interest 
        patient_ids : list, optional
            List of specific PatientIDs to process. If None, processes all patients
        index_date_df : pd.DataFrame, optional 
            DataFrame containing unique PatientIDs and their corresponding index dates. Only data for PatientIDs present in this DataFrame will be processed
        drop_stages : bool, default=True
            If True, drops original staging columns (GroupStage, TStage, and MStage) after creating modified versions
        drop_dates : bool, default=True
            If True, drops date columns (DiagnosisDate, MetDiagnosisDate, and CRPCDate) after calculating durations

        Returns
        -------
        pd.DataFrame
            - PatientID : object
                unique patient identifier
            - GroupStage_mod : category
                consolidated overall staging (I-IV and unknown) at time of first diagnosis
            - TStage_mod : category
                consolidated tumor staging (T1-T4 and unknown) at time of first diagnosis
            - NStage_mod : category
                consolidated lymph node staging (N0, N1, and unknown) at time of first diagnosis
            - MStage_mod : category
                consolidated metastasis staging (M0, M1, and unknown) at time of first diagnosis
            - GleasonScore_mod : category
                consolidated Gleason scores into Grade Groups (1-5 and unknown) at time of first diagnosis 
            - Histology : category
                histology (adenocarcinoma and NOS) at time of initial diagnosis 
            - days_diagnosis_to_met : float
                days from first diagnosis to metastatic disease 
            - met_diagnosis_year : category
                year of metastatic diagnosis 
            - IsCRPC : Int64
                binary (0/1) indicator for CRPC, determined by whether CRPC date is earlier than the index date 
            - days_diagnosis_to_crpc : float
                days from diagnosis to CRPC, calculated only when CRPC date is prior to index date (i.e., IsCRPC == 1)
            - PSADiagnosis : float, ng/mL
                PSA at time of first diagnosis
            - PSAMetDiagnosis : float
                PSA at time of metastatic diagnosis 
            - psa_doubling : float, months
                PSA doubling time for those with both a PSA at time of first and metastatic diagnosis, calculated only when PSA was higher at metastatic diagnosis than at initial diagnosis 
            - psa_velocity : float, ng/mL/month
                PSA velocity for those with both a PSA at time of first and metastatic diagnosis

            Original date columns (DiagnosisDate, MetDiagnosisDate, and CRPCDate) retained if drop_dates = False

        Notes
        -----
        Notable T-Stage consolidation decisions:
            - T0 is included in T1 
            - TX and Unknown/not documented are categorized as 'unknown' 

        Notable Gleanson score consolidation decisions: 
            - 7 (when breakdown not available) was placed into Grade Group 3

        PSA doubilng time formula: 
            - ln(2)/PSA slope
            - PSA slope = (ln(PSAMetDiagnosis) - ln(PSADiagnosis))/(MetDiagnosisDate - DiagnosisDate)

        PSA velocity formula: 
            - (PSAMetDiagnosis - PSADiagnosis)/(MetDiagnosisDate - DiagnosisDate)

        Output handling: 
        - Duplicate PatientIDs are logged as warnings if found but retained in output
        - Processed DataFrame is stored in self.enhanced_df
        """
        # Input validation
        if patient_ids is not None:
            if not isinstance(patient_ids, list):
                raise TypeError("patient_ids must be a list or None")
        
        if index_date_df is not None:
            if not isinstance(index_date_df, pd.DataFrame):
                raise ValueError("index_date_df must be a pandas DataFrame")
            if 'PatientID' not in index_date_df.columns:
                raise ValueError("index_date_df must contain a 'PatientID' column")
            if not index_date_column or index_date_column not in index_date_df.columns:
                raise ValueError('index_date_column not found in index_date_df')
            if index_date_df['PatientID'].duplicated().any():
                raise ValueError("index_date_df contains duplicate PatientID values, which is not allowed")

        try:
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read Enhanced_MetProstate.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            # Case 1: Using default MetDiagnosisDate with specific patients
            if index_date_column == 'MetDiagnosisDate' and patient_ids is not None:
                logging.info(f"Filtering for {len(patient_ids)} specific PatientIDs")
                df = df[df['PatientID'].isin(patient_ids)]
                logging.info(f"Successfully filtered Enhanced_MetProstate.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            # Case 2: Using custom index date with index_date_df
            elif index_date_column != 'MetDiagnosisDate' and index_date_df is not None:
                index_date_df[index_date_column] = pd.to_datetime(index_date_df[index_date_column])
                df = df[df.PatientID.isin(index_date_df.PatientID)]
                df = pd.merge(
                    df,
                    index_date_df[['PatientID', index_date_column]],
                    on = 'PatientID',
                    how = 'left'
                )
                logging.info(f"Successfully merged Enhanced_MetProstate.csv df with index_date_df resulting in shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            # Case 3: Using default MetDiagnosisDate with all patients (no filtering)
            elif index_date_column == 'MetDiagnosisDate' and patient_ids is None:
                logging.info(f"No filtering applied. Using all {df['PatientID'].nunique()} patients in the dataset")

            # Case 4: Error case - custom index date without index_date_df
            else:
                logging.error("If index_date_column is not 'MetDiagnosisDate', an index_date_df must be provided")
                return None
        
            # Convert categorical columns
            categorical_cols = ['GroupStage',
                                'TStage', 
                                'NStage',
                                'MStage', 
                                'GleasonScore', 
                                'Histology']
            
            df[categorical_cols] = df[categorical_cols].astype('category')

            # Recode stage variables using class-level mapping and create new column
            df['GroupStage_mod'] = df['GroupStage'].map(self.GROUP_STAGE_MAPPING).astype('category')
            df['TStage_mod'] = df['TStage'].map(self.T_STAGE_MAPPING).astype('category')
            df['NStage_mod'] = df['NStage'].map(self.N_STAGE_MAPPING).astype('category')
            df['MStage_mod'] = df['MStage'].map(self.M_STAGE_MAPPING).astype('category')
            df['GleasonScore_mod'] = df['GleasonScore'].map(self.GLEASON_MAPPING).astype('category')

            # Drop original stage variables if specified
            if drop_stages:
                df = df.drop(columns=['GroupStage', 'TStage', 'NStage', 'MStage', 'GleasonScore'])

            # Convert date columns to datetime
            date_cols = ['DiagnosisDate', 'MetDiagnosisDate', 'CRPCDate']
            for col in date_cols:
                df[col] = pd.to_datetime(df[col])

            # Generate new time-based variables 
            df['days_diagnosis_to_met'] = (df['MetDiagnosisDate'] - df['DiagnosisDate']).dt.days
            df['met_diagnosis_year'] = pd.Categorical(df['MetDiagnosisDate'].dt.year)

            # Recoding IsCRPC to be 1 if CRPCDate is less than or equal to index date 
            # Calculate time from diagnosis to CRPC (presuming before metdiagnosis or index)
            if index_date_column == "MetDiagnosisDate":
                df['IsCRPC'] = np.where(df['CRPCDate'] <= df['MetDiagnosisDate'], 1, 0)
                df['days_diagnosis_to_crpc'] = np.where(df['IsCRPC'] == 1,
                                                        (df['CRPCDate'] - df['DiagnosisDate']).dt.days,
                                                        np.nan)
            else:
                df['IsCRPC'] = np.where(df['CRPCDate'] <= df[index_date_column], 1, 0)
                df['days_diagnosis_to_crpc'] = np.where(df['IsCRPC'] == 1,
                                                        (df['CRPCDate'] - df['DiagnosisDate']).dt.days,
                                                        np.nan)

            num_cols = ['PSADiagnosis', 'PSAMetDiagnosis']
            for col in num_cols:
                df[col] = pd.to_numeric(df[col], errors = 'coerce').astype('float')

            # Calculating PSA doubling time in months 
            df_doubling = (
                df
                .query('DiagnosisDate.notna()')
                .query('days_diagnosis_to_met > 30') # At least 30 days from first diagnosis to metastatic diagnosis
                .query('PSADiagnosis.notna()')
                .query('PSAMetDiagnosis.notna()')
                .query('PSAMetDiagnosis > PSADiagnosis') # Doubling time formula only makes sense for rising numbers 
                .query('PSADiagnosis > 0') 
                .query('PSAMetDiagnosis > 0')  
                .assign(psa_doubling = lambda x: 
                        ((x['days_diagnosis_to_met']/30) * math.log(2))/
                        (np.log(x['PSAMetDiagnosis']) - 
                        np.log(x['PSADiagnosis']))
                        )
                [['PatientID', 'psa_doubling']]
            )

            # Calculating PSA velocity with time in months 
            df_velocity = (
                df
                .query('DiagnosisDate.notna()')
                .query('days_diagnosis_to_met > 30') # At least 30 days from first diagnosis to metastatic diagnosis
                .query('PSADiagnosis.notna()')
                .query('PSAMetDiagnosis.notna()')
                .query('PSADiagnosis > 0') 
                .query('PSAMetDiagnosis > 0') 
                .assign(psa_velocity = lambda x: (x['PSAMetDiagnosis'] - x['PSADiagnosis']) / (x['days_diagnosis_to_met']/30))
                [['PatientID', 'psa_velocity']]
            )

            final_df = pd.merge(df, df_doubling, on = 'PatientID', how = 'left')
            final_df = pd.merge(final_df, df_velocity, on = 'PatientID', how = 'left')

            if drop_dates:
                final_df = final_df.drop(columns = ['MetDiagnosisDate', 'DiagnosisDate', 'CRPCDate'])

            # Check for duplicate PatientIDs
            if len(final_df) > final_df['PatientID'].nunique():
                duplicate_ids = final_df[final_df.duplicated(subset = ['PatientID'], keep = False)]['PatientID'].unique()
                logging.warning(f"Duplicate PatientIDs found: {duplicate_ids}")

            logging.info(f"Successfully processed Enhanced_MetProstate.csv file with final shape: {final_df.shape} and unique PatientIDs: {(final_df['PatientID'].nunique())}")
            self.enhanced_df = final_df
            return final_df

        except Exception as e:
            logging.error(f"Error processing Enhanced_MetProstate.csv file: {e}")
            return None 
        
    def process_demographics(self,
                             file_path: str,
                             index_date_df: pd.DataFrame,
                             index_date_column: str,
                             drop_state: bool = True) -> pd.DataFrame:
        """
        Processes Demographics.csv by standardizing categorical variables, mapping states to census regions, and calculating age at index date.

        Parameters
        ----------
        file_path : str
            Path to Demographics.csv file
        index_date_df : pd.DataFrame, optional
            DataFrame containing unique PatientIDs and their corresponding index dates. Only demographic data for PatientIDs present in this DataFrame will be processed
        index_date_column : str, optional
            Column name in index_date_df containing index date
        drop_state : bool, default = True
            If True, drops State column after mapping to regions

        Returns
        -------
        pd.DataFrame
            - PatientID : object
                unique patient identifier
            - Race : category
                race (White, Black or African America, Asian, Other Race)
            - Ethnicity : category
                ethnicity (Hispanic or Latino, Not Hispanic or Latino)
            - age : Int64
                age at index date (index year - birth year)
            - region : category
                Maps all 50 states, plus DC and Puerto Rico (PR), to a US Census Bureau region
            - State : category
                US state (if drop_state=False)
            
        Notes
        -----
        Data cleaning and processing: 
        - Imputation for Race and Ethnicity:
            - If Race='Hispanic or Latino', Race value is replaced with NaN
            - If Race='Hispanic or Latino', Ethnicity is set to 'Hispanic or Latino'
            - Otherwise, missing Race and Ethnicity values remain unchanged
        - Ages calculated as <18 or >120 are logged as warning if found, but not removed
        - Missing States and Puerto Rico are imputed as unknown during the mapping to regions
        - Gender dropped since all males. 

        Output handling: 
        - Duplicate PatientIDs are logged as warnings if found but retained in output
        - Processed DataFrame is stored in self.demographics_df
        """
        # Input validation
        if not isinstance(index_date_df, pd.DataFrame):
            raise ValueError("index_date_df must be a pandas DataFrame")
        if 'PatientID' not in index_date_df.columns:
            raise ValueError("index_date_df must contain a 'PatientID' column")
        if not index_date_column or index_date_column not in index_date_df.columns:
            raise ValueError('index_date_column not found in index_date_df')
        if index_date_df['PatientID'].duplicated().any():
            raise ValueError("index_date_df contains duplicate PatientID values, which is not allowed")

        try:
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read Demographics.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            # Initial data type conversions
            df['BirthYear'] = df['BirthYear'].astype('Int64')
            df['State'] = df['State'].astype('category')

            index_date_df[index_date_column] = pd.to_datetime(index_date_df[index_date_column])

            # Select PatientIDs that are included in the index_date_df the merge on 'left'
            df = df[df.PatientID.isin(index_date_df.PatientID)]
            df = pd.merge(
                df,
                index_date_df[['PatientID', index_date_column]], 
                on = 'PatientID',
                how = 'left'
            )

            df['age'] = df[index_date_column].dt.year - df['BirthYear']

            # Age validation
            mask_invalid_age = (df['age'] < 18) | (df['age'] > 120)
            if mask_invalid_age.any():
                logging.warning(f"Found {mask_invalid_age.sum()} ages outside valid range (18-120)")

            # Drop the index date column and BirthYear after age calculation
            df = df.drop(columns = [index_date_column, 'BirthYear'])

            # Race and Ethnicity processing
            # If Race == 'Hispanic or Latino', fill 'Hispanic or Latino' for Ethnicity
            df['Ethnicity'] = np.where(df['Race'] == 'Hispanic or Latino', 'Hispanic or Latino', df['Ethnicity'])

            # If Race == 'Hispanic or Latino' replace with Nan
            df['Race'] = np.where(df['Race'] == 'Hispanic or Latino', np.nan, df['Race'])
            df[['Race', 'Ethnicity']] = df[['Race', 'Ethnicity']].astype('category')
            
            # Region processing
            # Group states into Census-Bureau regions  
            df['region'] = (df['State']
                            .map(self.STATE_REGIONS_MAPPING)
                            .fillna('unknown')
                            .astype('category'))

            # Drop State varibale if specified
            if drop_state:               
                df = df.drop(columns = ['State'])

            df = df.drop(columns = ['Gender'])

            # Check for duplicate PatientIDs
            if len(df) > df['PatientID'].nunique():
                duplicate_ids = df[df.duplicated(subset = ['PatientID'], keep = False)]['PatientID'].unique()
                logging.warning(f"Duplicate PatientIDs found: {duplicate_ids}")
            
            logging.info(f"Successfully processed Demographics.csv file with final shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")
            self.demographics_df = df
            return df

        except Exception as e:
            logging.error(f"Error processing Demographics.csv file: {e}")
            return None
        
    def process_practice(self,
                         file_path: str,
                         patient_ids: list = None) -> pd.DataFrame:
        """
        Processes Practice.csv to consolidate practice types per patient into a single categorical value indicating academic, community, or both settings.

        Parameters
        ----------
        file_path : str
            Path to Practice.csv file
        patient_ids : list, optional
            List of PatientIDs to process. If None, processes all patients

        Returns
        -------
        pd.DataFrame
            - PatientID : object
                unique patient identifier  
            - PracticeType_mod : category
                practice setting (ACADEMIC, COMMUNITY, or BOTH)

        Notes
        -----
        Output handling: 
        - PracticeID and PrimaryPhysicianID are removed 
        - Duplicate PatientIDs are logged as warnings if found but retained in output
        - Processed DataFrame is stored in self.practice_df
        """
        # Input validation
        if patient_ids is not None:
            if not isinstance(patient_ids, list):
                raise TypeError("patient_ids must be a list or None")
                
        try:
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read Practice.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            # Filter for specific PatientIDs if provided
            if patient_ids is not None:
                logging.info(f"Filtering for {len(patient_ids)} specific PatientIDs")
                df = df[df['PatientID'].isin(patient_ids)]
                logging.info(f"Successfully filtered Practice.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            df = df[['PatientID', 'PracticeType']]

            # Group by PatientID and get set of unique PracticeTypes
            grouped = df.groupby('PatientID')['PracticeType'].unique()
            grouped_df = pd.DataFrame(grouped).reset_index()

            # Function to determine the practice type
            def get_practice_type(practice_types):
                if len(practice_types) == 0:
                    return 'UNKNOWN'
                if len(practice_types) > 1:
                    return 'BOTH'
                return practice_types[0]
            
            # Apply the function to the column containing sets
            grouped_df['PracticeType_mod'] = grouped_df['PracticeType'].apply(get_practice_type).astype('category')

            final_df = grouped_df[['PatientID', 'PracticeType_mod']]

            # Check for duplicate PatientIDs
            if len(final_df) > final_df['PatientID'].nunique():
                duplicate_ids = final_df[final_df.duplicated(subset = ['PatientID'], keep = False)]['PatientID'].unique()
                logging.warning(f"Duplicate PatientIDs found: {duplicate_ids}")
            
            logging.info(f"Successfully processed Practice.csv file with final shape: {final_df.shape} and unique PatientIDs: {(final_df['PatientID'].nunique())}")
            self.practice_df = final_df
            return final_df

        except Exception as e:
            logging.error(f"Error processing Practice.csv file: {e}")
            return None
        
    def process_biomarkers(self,
                           file_path: str,
                           index_date_df: pd.DataFrame,
                           index_date_column: str, 
                           days_before: Optional[int] = None,
                           days_after: int = 0) -> pd.DataFrame:
        """
        Processes Enhanced_MetPC_Biomarkers.csv by determining biomarker status for each patient within a specified time window relative to an index date. 

        Parameters
        ----------
        file_path : str
            Path to Enhanced_MetPC_Biomarkers.csv file
        index_date_df : pd.DataFrame
            DataFrame containing unique PatientIDs and their corresponding index dates. Only biomarker data for PatientIDs present in this DataFrame will be processed
        index_date_column : str
            Column name in index_date_df containing the index date
        days_before : int | None, optional
            Number of days before the index date to include. Must be >= 0 or None. If None, includes all prior results. Default: None
        days_after : int, optional
            Number of days after the index date to include. Must be >= 0. Default: 0
        
        Returns
        -------
        pd.DataFrame
            - PatientID : object
                unique patient identifier
            - BRCA_status : category
                positive if ever-positive, negative if only-negative, otherwise unknown

        Notes
        ------
        Biomarker cleaning processing: 
        - BRCA status is classifed according to these as:
            - 'positive' if any test result is positive (ever-positive)
            - 'negative' if any test is negative without positives (only-negative) 
            - 'unknown' if all results are indeterminate
        
        - Missing biomarker data handling:
            - All PatientIDs from index_date_df are included in the output
            - Patients without any biomarker tests will have NaN values for all biomarker columns
            - Missing ResultDate is imputed with SpecimenReceivedDate

        Output handling: 
        - Duplicate PatientIDs are logged as warnings if found but retained in output
        - Processed DataFrame is stored in self.biomarkers_df
        """
        # Input validation
        if not isinstance(index_date_df, pd.DataFrame):
            raise ValueError("index_date_df must be a pandas DataFrame")
        if 'PatientID' not in index_date_df.columns:
            raise ValueError("index_date_df must contain a 'PatientID' column")
        if not index_date_column or index_date_column not in index_date_df.columns:
            raise ValueError('index_date_column not found in index_date_df')
        if index_date_df['PatientID'].duplicated().any():
            raise ValueError("index_date_df contains duplicate PatientID values, which is not allowed")
        
        if days_before is not None:
            if not isinstance(days_before, int) or days_before < 0:
                raise ValueError("days_before must be a non-negative integer or None")
        if not isinstance(days_after, int) or days_after < 0:
            raise ValueError("days_after must be a non-negative integer")

        try:
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read Enhanced_MetPC_Biomarkers.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            df['ResultDate'] = pd.to_datetime(df['ResultDate'])
            df['SpecimenReceivedDate'] = pd.to_datetime(df['SpecimenReceivedDate'])

            # Impute missing ResultDate with SpecimenReceivedDate
            df['ResultDate'] = np.where(df['ResultDate'].isna(), df['SpecimenReceivedDate'], df['ResultDate'])

            index_date_df[index_date_column] = pd.to_datetime(index_date_df[index_date_column])

            # Select PatientIDs that are included in the index_date_df the merge on 'left'
            df = df[df.PatientID.isin(index_date_df.PatientID)]
            df = pd.merge(
                    df,
                    index_date_df[['PatientID', index_date_column]],
                    on = 'PatientID',
                    how = 'left'
            )
            logging.info(f"Successfully merged Enhanced_MetPC_Biomarkers.csv df with index_date_df resulting in shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")
            
            # Create new variable 'index_to_result' that notes difference in days between resulted specimen and index date
            df['index_to_result'] = (df['ResultDate'] - df[index_date_column]).dt.days
            
            # Select biomarkers that fall within desired before and after index date
            if days_before is None:
                # Only filter for days after
                df_filtered = df[df['index_to_result'] <= days_after].copy()
            else:
                # Filter for both before and after
                df_filtered = df[
                    (df['index_to_result'] <= days_after) & 
                    (df['index_to_result'] >= -days_before)
                ].copy()

            # Process BRCA
            positive_values = {
                'BRCA1 mutation identified',
                'BRCA2 mutation identified',
                'Both BRCA1 and BRCA2 mutations identified',
                'BRCA mutation NOS' 
            }

            negative_values = {
                'No BRCA mutation',
                'Genetic Variant Favor Polymorphism',
            }

            brca_df = (
                df_filtered
                .query('BiomarkerName == "BRCA"')
                .groupby('PatientID')['BiomarkerStatus']
                .agg(lambda x: 'positive' if any(val in positive_values for val in x)
                    else ('negative' if any(val in negative_values for val in x)
                        else 'unknown'))
                .reset_index()
                .rename(columns={'BiomarkerStatus': 'BRCA_status'}) 
            )

            # Merge dataframes -- start with index_date_df to ensure all PatientIDs are included
            final_df = index_date_df[['PatientID']].copy()
            final_df = pd.merge(final_df, brca_df, on = 'PatientID', how = 'left')
            final_df['BRCA_status'] = final_df['BRCA_status'].astype('category')
            
            # Check for duplicate PatientIDs
            if len(final_df) > final_df['PatientID'].nunique():
                duplicate_ids = final_df[final_df.duplicated(subset = ['PatientID'], keep = False)]['PatientID'].unique()
                logging.warning(f"Duplicate PatientIDs found: {duplicate_ids}")

            logging.info(f"Successfully processed Enhanced_MetPC_Biomarkers.csv file with final shape: {final_df.shape} and unique PatientIDs: {(final_df['PatientID'].nunique())}")
            self.biomarkers_df = final_df
            return final_df

        except Exception as e:
            logging.error(f"Error processing Enhanced_MetPC_Biomarkers.csv file: {e}")
            return None
        
    def process_ecog(self, 
                     file_path: str,
                     index_date_df: pd.DataFrame,
                     index_date_column: str, 
                     days_before: int = 90,
                     days_after: int = 0, 
                     days_before_further: int = 180) -> pd.DataFrame:
        """
        Processes ECOG.csv to determine patient ECOG scores and progression patterns relative 
        to a reference index date. Uses two different time windows for distinct clinical purposes:
        
        1. A smaller window near the index date to find the most clinically relevant ECOG score
            that represents the patient's status at that time point
        2. A larger lookback window to detect clinically significant ECOG progression,
            specifically looking for patients whose condition worsened from ECOG 0-1 to ≥2

        Parameters
        ----------
        file_path : str
            Path to ECOG.csv file
        index_date_df : pd.DataFrame
            DataFrame containing unique PatientIDs and their corresponding index dates. Only ECOGs for PatientIDs present in this DataFrame will be processed
        index_date_column : str
            Column name in index_date_df containing the index date
        days_before : int, optional
            Number of days before the index date to include. Must be >= 0. Default: 90
        days_after : int, optional
            Number of days after the index date to include. Must be >= 0. Default: 0
        days_before_further : int, optional
            Number of days before index date to look for ECOG progression (0-1 to ≥2). Must be >= 0. Consider
            selecting a larger integer than days_before to capture meaningful clinical deterioration over time.
            Default: 180
            
        Returns
        -------
        pd.DataFrame
            - PatientID : object
                unique patient identifier
            - ecog_index : category, ordered 
                ECOG score (0-4) closest to index date
            - ecog_newly_gte2 : Int64
                binary indicator (0/1) for ECOG increased from 0-1 to ≥2 in larger lookback window 

        Notes
        ------
        Data cleaning and processing: 
        - The function selects the most clinically relevant ECOG score using the following priority rules:
            1. ECOG closest to index date is selected by minimum absolute day difference
            2. For equidistant measurements, higher ECOG score is selected
        
        Output handling: 
        - All PatientIDs from index_date_df are included in the output and values will be NaN for patients without ECOG values
        - Duplicate PatientIDs are logged as warnings if found but retained in output
        - Processed DataFrame is stored in self.ecog_df
        """
        # Input validation
        if not isinstance(index_date_df, pd.DataFrame):
            raise ValueError("index_date_df must be a pandas DataFrame")
        if 'PatientID' not in index_date_df.columns:
            raise ValueError("index_date_df must contain a 'PatientID' column")
        if not index_date_column or index_date_column not in index_date_df.columns:
            raise ValueError('index_date_column not found in index_date_df')
        if index_date_df['PatientID'].duplicated().any():
            raise ValueError("index_date_df contains duplicate PatientID values, which is not allowed")
        
        if not isinstance(days_before, int) or days_before < 0:
            raise ValueError("days_before must be a non-negative integer")
        if not isinstance(days_after, int) or days_after < 0:
            raise ValueError("days_after must be a non-negative integer")

        try:
            df = pd.read_csv(file_path)
            logging.info(f"Successfully read ECOG.csv file with shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")

            df['EcogDate'] = pd.to_datetime(df['EcogDate'])
            df['EcogValue'] = pd.to_numeric(df['EcogValue'], errors = 'coerce').astype('Int64')

            index_date_df[index_date_column] = pd.to_datetime(index_date_df[index_date_column])

            # Select PatientIDs that are included in the index_date_df the merge on 'left'
            df = df[df.PatientID.isin(index_date_df.PatientID)]
            df = pd.merge(
                df,
                index_date_df[['PatientID', index_date_column]],
                on = 'PatientID',
                how = 'left'
            )
            logging.info(f"Successfully merged ECOG.csv df with index_date_df resulting in shape: {df.shape} and unique PatientIDs: {(df['PatientID'].nunique())}")
                        
            # Create new variable 'index_to_ecog' that notes difference in days between ECOG date and index date
            df['index_to_ecog'] = (df['EcogDate'] - df[index_date_column]).dt.days
            
            # Select ECOG that fall within desired before and after index date
            df_closest_window = df[
                (df['index_to_ecog'] <= days_after) & 
                (df['index_to_ecog'] >= -days_before)].copy()

            # Find EcogValue closest to index date within specified window periods
            ecog_index_df = (
                df_closest_window
                .assign(abs_days_to_index = lambda x: abs(x['index_to_ecog']))
                .sort_values(
                    by=['PatientID', 'abs_days_to_index', 'EcogValue'], 
                    ascending=[True, True, False]) # Last False means highest ECOG is selected in ties 
                .groupby('PatientID')
                .first()
                .reset_index()
                [['PatientID', 'EcogValue']]
                .rename(columns = {'EcogValue': 'ecog_index'})
                .assign(
                    ecog_index = lambda x: x['ecog_index'].astype(pd.CategoricalDtype(categories = [0, 1, 2, 3, 4], ordered = True))
                    )
            )
            
            # Filter dataframe using farther back window
            df_progression_window = df[
                    (df['index_to_ecog'] <= days_after) & 
                    (df['index_to_ecog'] >= -days_before_further)].copy()
            
            # Create flag for ECOG newly greater than or equal to 2
            ecog_newly_gte2_df = (
                df_progression_window
                .sort_values(['PatientID', 'EcogDate']) 
                .groupby('PatientID')
                .agg({
                    'EcogValue': lambda x: (
                        # 1. Last ECOG is ≥2
                        (x.iloc[-1] >= 2) and 
                        # 2. Any previous ECOG was 0 or 1
                        any(x.iloc[:-1].isin([0, 1]))
                    )
                })
                .reset_index()
                .rename(columns={'EcogValue': 'ecog_newly_gte2'})
            )

            # Merge dataframes - start with index_date_df to ensure all PatientIDs are included
            final_df = index_date_df[['PatientID']].copy()
            final_df = pd.merge(final_df, ecog_index_df, on = 'PatientID', how = 'left')
            final_df = pd.merge(final_df, ecog_newly_gte2_df, on = 'PatientID', how = 'left')
            
            # Assign datatypes 
            final_df['ecog_index'] = final_df['ecog_index'].astype(pd.CategoricalDtype(categories=[0, 1, 2, 3, 4], ordered=True))
            final_df['ecog_newly_gte2'] = final_df['ecog_newly_gte2'].astype('Int64')

            # Check for duplicate PatientIDs
            if len(final_df) > final_df['PatientID'].nunique():
                duplicate_ids = final_df[final_df.duplicated(subset = ['PatientID'], keep = False)]['PatientID'].unique()
                logging.warning(f"Duplicate PatientIDs found: {duplicate_ids}")
                
            logging.info(f"Successfully processed ECOG.csv file with final shape: {final_df.shape} and unique PatientIDs: {(final_df['PatientID'].nunique())}")
            self.ecog_df = final_df
            return final_df

        except Exception as e:
            logging.error(f"Error processing ECOG.csv file: {e}")
            return None