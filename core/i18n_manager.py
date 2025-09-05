# -*- coding: utf-8 -*-
"""
Internationalization manager for bilingual support (English/Indonesian)
"""

import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QLocale

class I18nManager:
    """Manages translations between English and Indonesian"""
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'id': 'Bahasa Indonesia'
    }
    
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.i18n_path = os.path.join(plugin_dir, 'i18n')
        self.translator = None
        self.current_language = 'en'
        
        # Create i18n directory if it doesn't exist
        if not os.path.exists(self.i18n_path):
            os.makedirs(self.i18n_path)
    
    def get_translator(self):
        """Get translator for current locale"""
        locale = QSettings().value('locale/userLocale', 'en_US')[0:2]
        
        # Check if Indonesian
        if locale == 'id':
            self.current_language = 'id'
        else:
            self.current_language = 'en'
        
        locale_path = os.path.join(
            self.i18n_path,
            f'ShipwreckExcavation_{self.current_language}.qm'
        )
        
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            return self.translator
        
        return None
    
    def set_language(self, language_code):
        """Set the application language"""
        if language_code in self.SUPPORTED_LANGUAGES:
            self.current_language = language_code
            return True
        return False
    
    def get_current_language(self):
        """Get current language code"""
        return self.current_language
    
    def translate(self, text, context='ShipwreckExcavation'):
        """Translate text based on current language"""
        # For now, return the text as-is
        # In production, this would use Qt's translation system
        return text
    
    @staticmethod
    def get_translations():
        """Get common translations dictionary"""
        return {
            'en': {
                # Main UI
                'Shipwreck Excavation Management': 'Shipwreck Excavation Management',
                'Sites': 'Sites',
                'Finds': 'Finds',
                'Media': 'Media',
                'Dive Logs': 'Dive Logs',
                'Workers': 'Workers',
                'Costs': 'Costs',
                'Settings': 'Settings',
                
                # Database
                'Create New Database': 'Create New Database',
                'Open Database': 'Open Database',
                'Database': 'Database',
                
                # Finds
                'Find Number': 'Find Number',
                'Material Type': 'Material Type',
                'Object Type': 'Object Type',
                'Description': 'Description',
                'Condition': 'Condition',
                'Find Date': 'Find Date',
                'Depth (m)': 'Depth (m)',
                'Coordinates': 'Coordinates',
                
                # Materials
                'Ceramic': 'Ceramic',
                'Metal': 'Metal',
                'Wood': 'Wood',
                'Glass': 'Glass',
                'Stone': 'Stone',
                'Bone': 'Bone',
                'Textile': 'Textile',
                'Other': 'Other',
                
                # Conditions
                'Excellent': 'Excellent',
                'Good': 'Good',
                'Fair': 'Fair',
                'Poor': 'Poor',
                'Fragment': 'Fragment',
                
                # Actions
                'Add': 'Add',
                'Edit': 'Edit',
                'Delete': 'Delete',
                'Save': 'Save',
                'Cancel': 'Cancel',
                'Search': 'Search',
                'Export': 'Export',
                'Import': 'Import',
                'Sync': 'Sync',
                
                # Messages
                'Success': 'Success',
                'Error': 'Error',
                'Warning': 'Warning',
                'Info': 'Info',
                'Confirm Delete': 'Are you sure you want to delete this item?',
                'No items found': 'No items found',
                'Required field': 'This field is required',
            },
            'id': {
                # Main UI
                'Shipwreck Excavation Management': 'Manajemen Ekskavasi Kapal Karam',
                'Sites': 'Situs',
                'Finds': 'Temuan',
                'Media': 'Media',
                'Dive Logs': 'Log Penyelaman',
                'Workers': 'Pekerja',
                'Costs': 'Biaya',
                'Settings': 'Pengaturan',
                
                # Database
                'Create New Database': 'Buat Database Baru',
                'Open Database': 'Buka Database',
                'Database': 'Database',
                
                # Finds
                'Find Number': 'Nomor Temuan',
                'Material Type': 'Jenis Material',
                'Object Type': 'Jenis Objek',
                'Description': 'Deskripsi',
                'Condition': 'Kondisi',
                'Find Date': 'Tanggal Temuan',
                'Depth (m)': 'Kedalaman (m)',
                'Coordinates': 'Koordinat',
                
                # Materials
                'Ceramic': 'Keramik',
                'Metal': 'Logam',
                'Wood': 'Kayu',
                'Glass': 'Kaca',
                'Stone': 'Batu',
                'Bone': 'Tulang',
                'Textile': 'Tekstil',
                'Other': 'Lainnya',
                
                # Conditions
                'Excellent': 'Sangat Baik',
                'Good': 'Baik',
                'Fair': 'Cukup',
                'Poor': 'Buruk',
                'Fragment': 'Pecahan',
                
                # Actions
                'Add': 'Tambah',
                'Edit': 'Ubah',
                'Delete': 'Hapus',
                'Save': 'Simpan',
                'Cancel': 'Batal',
                'Search': 'Cari',
                'Export': 'Ekspor',
                'Import': 'Impor',
                'Sync': 'Sinkronisasi',
                
                # Messages
                'Success': 'Berhasil',
                'Error': 'Kesalahan',
                'Warning': 'Peringatan',
                'Info': 'Informasi',
                'Confirm Delete': 'Apakah Anda yakin ingin menghapus item ini?',
                'No items found': 'Tidak ada item ditemukan',
                'Required field': 'Bidang ini wajib diisi',
            }
        }