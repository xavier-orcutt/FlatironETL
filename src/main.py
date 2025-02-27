import pandas as pd
from nsclc import DataProcessorNSCLC
from merge_utils import merge_dataframes
from IPython import embed     

if __name__ == "__main__":
    processor = DataProcessorNSCLC()

    enhanced_file_path = "data_nsclc/Enhanced_AdvancedNSCLC.csv"
    demographics_file_path = "data_nsclc/Demographics.csv"
    practice_file_path = "data_nsclc/Practice.csv"
    mortality_file_path = "data_nsclc/Enhanced_Mortality_V2.csv"
    biomarkers_file_path = "data_nsclc/Enhanced_AdvNSCLCBiomarkers.csv"
    ecog_file_path = "data_nsclc/ECOG.csv"
    vitals_file_path = "data_nsclc/Vitals.csv"
    lab_file_path =  "data_nsclc/Lab.csv"
    medication_file_path =  "data_nsclc/MedicationAdministration.csv"
    diagnosis_file_path = "data_nsclc/Diagnosis.csv"
    insurance_file_path = "data_nsclc/Insurance.csv"

    df = pd.read_csv(enhanced_file_path)
    
    # Process datasets
    enhanced_df = processor.process_enhanced_adv(enhanced_file_path)

    demographics_df = processor.process_demographics(demographics_file_path, 
                                                     index_date_df=df, 
                                                     index_date_column='AdvancedDiagnosisDate')
    
    practice_df = processor.process_practice(practice_file_path)

    mortality_df = processor.process_mortality(mortality_file_path,
                                               index_date_df=df,
                                               index_date_column='AdvancedDiagnosisDate',
                                               visit_path="data/Visit.csv",
                                               oral_path="data/Enhanced_AdvUrothelial_Orals.csv",
                                               drop_dates = False)
    
    biomarkers_df = processor.process_biomarkers(biomarkers_file_path,
                                                 index_date_df=df,
                                                 index_date_column='AdvancedDiagnosisDate',
                                                 days_before=None,
                                                 days_after=14)

    ecog_df =  processor.process_ecog(ecog_file_path,
                                      index_date_df=df,
                                      index_date_column='AdvancedDiagnosisDate',
                                      days_before=90,
                                      days_after=0)
    
    vitals_df = processor.process_vitals(vitals_file_path,
                                         index_date_df=df,
                                         index_date_column='AdvancedDiagnosisDate',
                                         weight_days_before = 90,
                                         days_after = 0,
                                         vital_summary_lookback = 180,
                                         abnormal_reading_threshold = 1)
    
    labs_df = processor.process_labs(lab_file_path,
                                     index_date_df=df,
                                     index_date_column='AdvancedDiagnosisDate',
                                     days_before = 90,
                                     days_after = 0,
                                     summary_lookback = 180)
    
    medications_df = processor.process_medications(medication_file_path,
                                                  index_date_df = df,
                                                  index_date_column='AdvancedDiagnosisDate',
                                                  days_before=180,
                                                  days_after=0)
    

    diagnosis_df = processor.process_diagnosis(diagnosis_file_path,
                                               index_date_df = df,
                                               index_date_column='AdvancedDiagnosisDate',
                                               days_before=None,
                                               days_after=0)
    
    insurance_df = processor.process_insurance(insurance_file_path,
                                               index_date_df = df,
                                               index_date_column='AdvancedDiagnosisDate',
                                               days_before=None,
                                               days_after=0,
                                               missing_date_strategy = 'conservative')
    


    # Merge datasets
    merged_data = merge_dataframes(enhanced_df, 
                                   demographics_df,
                                   practice_df,
                                   biomarkers_df,
                                   ecog_df,
                                   vitals_df,
                                   insurance_df,
                                   labs_df,
                                   medications_df,
                                   diagnosis_df,
                                   mortality_df)
    
    if merged_data is not None:
        print(merged_data.head())
        print(merged_data.dtypes)
        embed()