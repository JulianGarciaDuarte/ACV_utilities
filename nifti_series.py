import os
import copy
import nibabel as nb

series_to_fetch = ['adc', 'dwi']
mask_config = {
    'full_match': True
}
series_config = {
    'try_full_match': True
}

class Series:
    """
    Parameters:
        - series_type: The kind of series. E.g. 'adc', 'dwi', etc.
        - path: The path to the image in the server
    """
    def __init__(self, series_type, path):
        self.series_type = series_type
        self.path = path
        
    def get_path(self):
        return self.path
    
    def get_type(self):
        return self.series_type
    
    def get_data(self):
        # WARNING! JUST TAKES THE FIRST PATH 
        # THIS SHOULD NOT BE THIS WAY. 
        # SUPPORT TO MULTIPLE PATHS MUST BE
        # IMPLEMENTED OR PATH SHOULD BE 
        # STRING, NOT LIST
        return nb.load(self.path[0]).get_fdata()
    
class Mask(Series):
    """
    Parameters:
        - doctor: The doctor who made the mask.
    """
    def __init__(self, series_type, path, doctor=None):
        super().__init__(series_type, path)
        self.doctor=doctor
        
    def get_doctor(self):
        return self.doctor

class Patient:
    """
    Parametros:
        - images: Dictionary of Series objects 
        - masks: Dictionary of Mask objects
        - path: Absolute path to the folder of the patient
    
    Methods:
        - fetch_series(series_list, file_extension='.nii.gz', **kwargs)
            Fetches the series given the series list and file extension. To include a 
            path, there MUST be a folder which name contains exclusively the name of 
            one series and a file with the extension provided in the file_extension
            argument.
            The search is performed from the path of the patient.
            
        - fetch_masks(series_list, file_extension='.nii.gz', verbose=0)
            Fetches the paths of the masks under a subfolder named as MASKS. All subfolders
            under the masks folder will be considered as doctor's folders and files found in
            those folders will be tagged with the docto'r folder name. Files directly found
            under the masks folder will be tagged with None as the doctor who made the mask.
            The verbose argument displays information about the execution of the method.
            The search is performed from the path of the patient.
            
        - fetch_all(series_list, file_extension='.nii.gz', verbose)
            Fetches both series and masks within the path of the patient.
            For more information see the documentation of the fetch_series and fetch_masks 
            methods.
            The verbose argument displays information about the execution of the method.
    """
    images = {}
    masks = {}
    
    def __init__(self, patient_id, patient_path, warnings_file=None, logs_file=None):
        self.patient_id=patient_id
        self.path=patient_path
        
        # Crea el archivo de warnings si no existe
        if warnings_file is None:
            open('warnings.txt', 'a').close()
            self.warnings_file = os.path.join(os.getcwd(), 'warnings.txt')
        else:
            open(warnings_file, 'a').close()
            self.warnings_file = warnings_file
            
        # Crea el archivo de logs si no existe
        if logs_file is None:
            open('logs.txt', 'a').close()
            self.logs_file = os.path.join(os.getcwd(), 'logs.txt')
        else:
            open(logs_file, 'a').close()
            self.logs_file = logs_file
        
    def _check_exception_words(self, file_name, exceptions):
        """
        If file name contains any of the words includeded in exceptions
        it returns False, else return True
        """
        if exceptions is None:
            return True
        
        for excp in exceptions:
            if excp in file_name:
                # Writes to logs
                self._write_log(f'file excluded {file_name} by exception: {excp}')
                return False
        return True
    
    def _create_mask(self, series_desc, path, doctor):
        if series_desc is None or path is None:
            return None
        # Checks for an empty path
        elif not path:
            return None
        else: return Mask(series_desc, path, doctor)
    
    def _create_series(self, series_desc, path):
        if series_desc is None or path is None:
            return None
        elif not path:
            return None
        else: return Series(series_desc, path)
    
    def _fetch_single_series(self, 
                             series_desc, 
                             file_extension='.nii.gz', 
                             warnings=True, 
                             exceptions=None, 
                             full_match=False,
                             try_full_match=False):
        """
        Fetches a single series's path (e.g. adc, dwi, etc) from the patient folder
        (patient path).
        First, it looks for a folder that contains the name of the series and all the 
        files within that folder with the given extension will be considered as a series.
        If there is no folder with that name or there is no files that matches the extension
        returns None.
        The warnings argument writes to a warnings folder if the name of a file does not
        match exactly the series_desc.
        
         - exceptions: (list) If not None, final paths are checked to exclude file names that contain
             any word in the exceptions list.
        - full_match: (Boolean) If True the name of the file MUST be equal to the series_desc argument.
            If given, try_full_match parameter is not used.
        - try_full_match: (Boolean) If True tries to find a full match. If no full match is found, takes 
            the rest of the images as series. (Excluding the exceptions)

        """
        # Looks for a folder with the series_desc name
        folder_list = [os.path.join(self.path, folder) for folder in os.listdir(self.path) if series_desc.lower() in folder.lower()]
        
        # Write to logs
        self._write_log(f'Folders found for {series_desc}: {folder_list}')
        
        if len(folder_list) > 1 and warnings:
            # Writes an alert about the multiple folder issue
            message = f'More than one series folder found with series_desc: {series_desc}'
            message += f'\n paths: {folder_list}'
            self.write_warning(message)
            
        # Fetches the .nii.gz files
        file_list = []
        for folder in folder_list:
            # Write to logs
            self._write_log(f'Files found in {folder} folder: {os.listdir(folder)}')
            # Write to logs
            log_message = f'From _fetch_single_series: execute _select_files with parameters'
            log_message += f'SER_DESC: {series_desc} - exceptions: {exceptions} - try_full_match: {try_full_match}'
            log_message += f'- full_match: {full_match}'
            self._write_log(log_message)
            file_list += self._select_files(series_desc, 
                                            folder, 
                                            file_extension,
                                            exceptions=exceptions, 
                                            full_match=full_match, 
                                            try_full_match=try_full_match)
            

        # Write to logs
        self._write_log(f'Files selected to series objects {file_list}')
        
        # Creates the series objects
        series_list = []
        for path in file_list:
            series_list.append(self._create_series(series_desc, path))
            
        return series_list
    
    def _fetch_single_mask(self, 
                             series_desc, 
                             file_extension='.nii.gz', 
                             warnings=True, 
                             exceptions=None, 
                             full_match=False,
                             try_full_match=False):
        """
        Fetches a single mask's path (e.g. adc, dwi, etc) from the patient folder
        (patient path).
        First, it looks for a folder named MASKS, the subfolders under MASKS will be considered
        as the name of the doctors for the masks under those folders.
        
        The warnings argument writes to a warnings folder if the name of a file does not
        match exactly the series_desc.
        
         - exceptions: (list) If not None, final paths are checked to exclude file names that contain
             any word in the exceptions list.
        - full_match: (Boolean) If True the name of the file MUST be equal to the series_desc argument.
            If given, try_full_match parameter is not used.
        - try_full_match: (Boolean) If True tries to find a full match. If no full match is found, takes 
            the rest of the images as series. (Excluding the exceptions)

        """
        mask_folder_name = 'masks'
        # Looks for a folder named masks
        masks_folder_list = [os.path.join(self.path, folder) 
                       for folder in os.listdir(self.path) if mask_folder_name.lower() in folder.lower()]
        
        # Checks how many masks folders there are ONLY ONE IS EXPECTED
        if len(masks_folder_list) > 1:
            self._write_warning(f'CRITICAL! - {len(mask_folder_list)} masks folders found when ONLY ONE IS EXPECTED')
            self._write_log(f'{len(mask_folder_list)} mask folders list found, taking only the first.')
        
        # Takes always the first folder since only one is expected
        mask_folder_path = os.path.join(self.path, masks_folder_list[0])
        
        # Gets all the doctor's folders
        doctors_list = [folder for folder in os.listdir(mask_folder_path)
                        if os.path.isdir(os.path.join(mask_folder_path, folder))]
            
        # Fetches the .nii.gz files
        file_dict = {doctor:[] for doctor in doctors_list}
        for doctor in doctors_list:
            # Gets the folder path 
            folder = os.path.join(mask_folder_path, doctor)
            
            # Write to logs
            self._write_log(f'Files found in {folder} folder: {os.listdir(folder)}')
            # Write to logs
            log_message = f'From _fetch_single_mask: execute _select_files with parameters'
            log_message += f'SER_DESC: {series_desc} - exceptions: {exceptions} - try_full_match: {try_full_match}'
            log_message += f'- full_match: {full_match}'
            self._write_log(log_message)
            file_dict[doctor] += self._select_files(series_desc, 
                                            folder, 
                                            file_extension,
                                            exceptions=exceptions, 
                                            full_match=full_match, 
                                            try_full_match=try_full_match)
            

        # Write to logs
        self._write_log(f'Files selected to masks objects {file_dict.values()}')

        # Creates the masks objects
        masks_dict = {doctor:[] for doctor in doctors_list}
        for doctor, path in file_dict.items():
            masks_dict[doctor].append(self._create_mask(series_desc, path, doctor))
            
        return copy.deepcopy(masks_dict)
    
    def _select_files(self, series_desc, folder, file_extension, exceptions=None, full_match=False, try_full_match=False):
        """
        Check if the given folder path matches the series desc parameter and doesn't 
        contains any of the exception words. If full_match parameter is specified 
        try_full_match parameter is not used.
        """
        result = []
        if full_match or try_full_match:
            # Checks for a full match
            result = [os.path.join(folder, file) for file in os.listdir(folder) 
                          if file.lower() == ''.join([series_desc.lower(), file_extension])
                         and self._check_exception_words(file, exceptions)]

        if (not full_match and try_full_match == False) or (try_full_match and len(result) ==0):
            # Checks for all files excluding the exceptions
            result = [os.path.join(folder, file) for file in os.listdir(folder) 
                          if file_extension in file
                         and self._check_exception_words(file, exceptions)]
        return result
        
    def _write_log(self, message):
        message = f'\nPID:{self.patient_id} - {message}'
        with open(self.logs_file, 'a') as logs:
            logs.writelines(message)
            
    def _write_warning(self, message):
        message = f'\nWARNING {self.patient_id} - {message}'
        with open(self.warnings_file, 'a') as warnings:
            warnings.writelines(message)
    
    def count_masks_overall(self):
        type_count = self.count_masks_per('series_type')
        doctor_count = self.count_masks_per('doctor')
        
        return {**type_count, **doctor_count}
    
    def count_masks_per(self, count_type):
        """
        Retrieves the type of the masks that the patient actually has. 
        This takes the type directly from the series object in order to
        ensure that there is a Series object associated with that count_type.
        
        - type: This parameter only has 2 posible values: 'doctor', 'series_type'
            and it decides over what discriminator compute the count
        """
        
        # TEMPORARY SHOULD BE FIXED. 
        # TODO: The patient doesn't store his state from fetch_patients
        self.fetch_all(series_to_fetch, mask_config, series_config)
            
        if count_type.lower() == 'series_type':
            count = {mask_type: 0 for mask_type in self.masks.keys()}
        elif count_type.lower() == 'doctor':
            count = {doctor: 0 for doctor in next(iter(self.masks.values())).keys()}
        else:
            raise Exception('Invalid count_type')
        
        for mask_type, doctor_dict in self.masks.items():
            if doctor_dict is not None:
                for doctor, mask_list in doctor_dict.items():
                    for mask in mask_list:
                        if mask is not None:
                            
                            if count_type.lower() == 'series_type':
                                count[mask.get_type()] += 1
                            elif count_type.lower() == 'doctor':
                                count[mask.get_doctor()] += 1
        
        return count
    
    def count_series_per_type(self):
        # TEMPORARY SHOULD BE FIXED. 
        # TODO: The patient doesn't store his state from fetch_patients
        self.fetch_all(series_to_fetch, mask_config, series_config)
        count = {series_type: 0 for series_type in self.images.keys()}
        
        for series_list in self.images.values():
            if series_list is not None or len(series_list) > 1:
                for series in series_list:
                    if series is not None:
                        count[series.get_type()] += 1
        
        return count
    
    def fetch_all(self, series_list, mask_config, series_config):
        data = {}
        data['masks'] = self.fetch_masks(series_list, **mask_config)
        data['series'] = self.fetch_series(series_list, **series_config)
        return data
    
    def fetch_masks(self, series_list, file_extension='.nii.gz', **kwargs):
        for ser_desc in series_list:
            # Write to logs
            message = f'Run self._fetch_single_mask with configuration: '
            message += f'SER: {ser_desc} - file_ext: {file_extension} '
            for key, value in kwargs.items():
                message += f'{key}:{value} - '
            self._write_log(message)
            
            # Fetches the masks
            self.masks[ser_desc] = self._fetch_single_mask(ser_desc, file_extension=file_extension, **kwargs)
            
        return copy.deepcopy(self.masks)

    def fetch_series(self, series_list, file_extension='.nii.gz', **kwargs):
        for ser_desc in series_list:
            # Write to logs
            message = f'Run self._fetch_single_series with configuration: '
            message += f'SER: {ser_desc} - file_ext: {file_extension} '
            for key, value in kwargs.items():
                message += f'{key}:{value} - '
            self._write_log(message)
            
            self.images[ser_desc] = self._fetch_single_series(ser_desc, file_extension=file_extension, **kwargs)
        return self.images
    
    def get_id(self):
        return self.patient_id
    
    def get_series_types(self):
        """
        Retrieves the type of the series that the patient actually has. 
        This takes the type directly from the series object in order to
        ensure that there is a Series object associated with that type.
        """
        series_type_list = []
        for series_type, series_list in self.images.items():
            if series_list is not None:
                
                if len(series_list) > 1:
                    # Writes a warning
                    self._write_warning(f'Paient has multiple series for type: {series_type}')
                for series in series_list:
                    series_type_list.append(series.get_type())
        
        return set(series_type_list)
    
    def get_series_by_type(self, series_type):
        # TEMPORARY SHOULD BE FIXED. 
        # TODO: The patient doesn't store his state from fetch_patients
        self.fetch_all(series_to_fetch, mask_config, series_config)
        return self.images[series_type]
    
    def get_mask_list(self):
        """
        Returns a list of all masks asociated with the patient
        """
        # TEMPORARY SHOULD BE FIXED. 
        # TODO: The patient doesn't store his state from fetch_patients
        self.fetch_all(series_to_fetch, mask_config, series_config)
        result = []
        
        for mask_per_doctor in self.masks.values():
            for mask_list in mask_per_doctor.values():
                for mask in mask_list:
                    if mask is not None:
                        result.append(mask)
        return result
        
class DatasetDiscover:
    """
    Parameters:
        - root: Path that contains all the folders with the patient's information
        - patients: Dictionary of Patient objects
    
    Methods:
        - fetch_patients()
    """
    patients = {}
    def_mask_config = {'full_match': True}
    def_series_config = {'try_full_match': True}
    
    def __init__(self, root):
        self.root = root
        
    def fetch_patients(self, patient_id_list, modalities, mask_config=None, series_config=None):
        if mask_config is None:
            mask_config = self.def_mask_config
        if series_config is None:
            series_config = self.def_series_config
            
        for patient_id in patient_id_list:
            patient_path = os.path.join(self.root, patient_id)
            if not os.path.isdir(patient_path):
                continue
                
            # Fetch the patient and its series and masks
            patient = Patient(patient_id, patient_path)
            #patient.fetch_all(modalities, mask_config, series_config)
            self.patients[patient_id] = patient
            
        return self.patients
    
    def get_patients_by_mask_count(self, count_type, rule):
        """
        Applies a function to the result of the count_type
        per patient. The rule function must return a boolean 
        value which in case to be True will include the patient
        in the returned list.
        
        The rule function must take as keyworded arguments
        the resulting dictionary of the count, either doctor
        or series_type count.
        """
        selected = []
        for patient in self.patients.values():
            count = patient.count_masks_per(count_type=count_type)
            if rule(**count):
                selected.append(patient)
        return selected
    
    def get_overall_mask_count(self):
        result = {}
        for patient in self.patients.values():
            result[patient.get_id()] = patient.count_masks_overall()
        
        return result
    
    def get_series_type_count(self):
        result = {}
        for patient in self.patients.values():
            result[patient.get_id()] = patient.count_series_per_type()
        
        return result
    
    def get_series_paths(self, series_type):
        result = {}
        for patient in self.patients.values():
            result[patient.get_id()] = [ser.get_path() for ser in patient.get_series_by_type(series_type)]
        
        return result

