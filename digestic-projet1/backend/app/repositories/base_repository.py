import json
import os
from typing import List, Optional, TypeVar, Generic
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Repository de base pour gérer les données dans des fichiers JSON"""
    
    def __init__(self, data_dir: str, filename: str):
        self.data_dir = data_dir
        self.filename = filename
        self.file_path = os.path.join(data_dir, filename)
        self._ensure_data_dir()
        self._ensure_file()
    
    def _ensure_data_dir(self):
        """Crée le dossier de données s'il n'existe pas"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _ensure_file(self):
        """Crée le fichier JSON s'il n'existe pas"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _read_data(self) -> List[dict]:
        """Lit toutes les données du fichier"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_data(self, data: List[dict]):
        """Écrit les données dans le fichier"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @abstractmethod
    def _model_from_dict(self, data: dict) -> T:
        """Convertit un dictionnaire en modèle"""
        pass
    
    @abstractmethod
    def _model_to_dict(self, model: T) -> dict:
        """Convertit un modèle en dictionnaire"""
        pass
    
    def find_all(self) -> List[T]:
        """Récupère tous les éléments"""
        data = self._read_data()
        return [self._model_from_dict(item) for item in data]
    
    def find_by_id(self, id: str) -> Optional[T]:
        """Récupère un élément par son ID"""
        data = self._read_data()
        for item in data:
            if item.get('id') == id:
                return self._model_from_dict(item)
        return None
    
    def create(self, model: T) -> T:
        """Crée un nouvel élément"""
        data = self._read_data()
        model_dict = self._model_to_dict(model)
        data.append(model_dict)
        self._write_data(data)
        return model
    
    def update(self, id: str, model: T) -> Optional[T]:
        """Met à jour un élément"""
        data = self._read_data()
        for i, item in enumerate(data):
            if item.get('id') == id:
                model_dict = self._model_to_dict(model)
                data[i] = model_dict
                self._write_data(data)
                return model
        return None
    
    def delete(self, id: str) -> bool:
        """Supprime un élément"""
        data = self._read_data()
        initial_length = len(data)
        data = [item for item in data if item.get('id') != id]
        if len(data) < initial_length:
            self._write_data(data)
            return True
        return False
    
    def find_by(self, **kwargs) -> List[T]:
        """Recherche des éléments par critères"""
        data = self._read_data()
        results = []
        for item in data:
            match = all(item.get(key) == value for key, value in kwargs.items())
            if match:
                results.append(self._model_from_dict(item))
        return results


