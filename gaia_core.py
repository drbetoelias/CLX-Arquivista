import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class XSSRD:
    """Layer de limpeza semântica: elimina ruído, preserva intenção."""

    FILLER_PATTERNS = [
        "tipo assim",
        "né",
        "sabe",
        "tipo",
        "meio",
        "mais ou menos",
        "na verdade",
        "olha",
        "cara",
        "tá",
        "então",
        "bem",
        "sei lá",
        "olha só",
        "você sabe",
        "eu acho",
        "parece que",
    ]

    @staticmethod
    def normalize_spaces(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def remove_filler(cls, text: str) -> str:
        cleaned = text
        for phrase in cls.FILLER_PATTERNS:
            cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned, flags=re.IGNORECASE)
        return cls.normalize_spaces(cleaned)

    @staticmethod
    def remove_repetitions(text: str) -> str:
        # remove repetições simples como "cansado cansado" ou "tipo tipo"
        return re.sub(r"\b(\w+)(?:\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        return re.findall(r"\d+(?:[.,]\d+)?", text)

    @staticmethod
    def extract_emotions(text: str) -> Dict[str, bool]:
        signals = {
            "cansado": bool(re.search(r"\bcansado\b|\bfadig\w+\b|\bexausto\b", text, flags=re.IIGNORECASE)),
            "triste": bool(re.search(r"\btriste\b|\bdesanim\w+\b|\bbaixa\b", text, flags=re.IIGNORECASE)),
            "feliz": bool(re.search(r"\bfeliz\b|\balegre\b|\bcontente\b|\bótimo\b", text, flags=re.IIGNORECASE)),
            "bravo": bool(re.search(r"\bbravo\b|\bfurioso\b|\bira\b|\benfurec\w+\b", text, flags=re.IIGNORECASE)),
            "medo": bool(re.search(r"\bmedo\b|\breceio\b|\bapreens\w+\b|\bansioso\b", text, flags=re.IIGNORECASE)),
            "saude": bool(re.search(r"\bdiab\w+\b|\bglaucoma\b|\bpress\w+\b|\bsono\b|\bsaude\b", text, flags=re.IIGNORECASE)),
        }
        return signals

    @staticmethod
    def infer_intensity(text: str) -> str:
        strong = ["muito", "muito muito", "extremamente", "grave", "crítico", "urgente", "muita", "altíssimo", "intenso"]
        medium = ["mais ou menos", "bastante", "normalmente", "forte", "importante"]
        lower = ["um pouco", "levemente", "pouco"]
        t = text.lower()
        if any(word in t for word in strong):
            return "alta"
        if any(word in t for word in medium):
            return "media"
        if any(word in t for word in lower):
            return "baixa"
        return "media"

    @staticmethod
    def classify_category(text: str) -> str:
        categories = [
            ("saude", ["diab", "glaucoma", "pressao", "sono", "medic", "saude"]),
            ("juridico", ["contrato", "licenca", "processo", "juridico", "documento", "prova"]),
            ("financeiro", ["dinheiro", "pagamento", "negocio", "valor", "conta", "invest"]),
            ("emocional", ["ansioso", "triste", "cansado", "rage", "emocao", "psic", "estresse"]),
            ("projeto", ["projeto", "gaia", "arquivista", "xssrd", "sistema", "codig", "repositorio"]),
        ]
        for name, patterns in categories:
            if any(p for p in patterns if p in text.lower()):
                return name
        return "geral"

    @classmethod
    def clean(cls, text: str) -> str:
        t = cls.remove_filler(text)
        t = cls.remove_repetitions(t)
        t = cls.normalize_spaces(t)
        return t

    @classmethod
    def extract_semantics(cls, text: str) -> Dict[str, Any]:
        clean = cls.clean(text)
        return {
            "text": clean,
            "numbers": cls.extract_numbers(clean),
            "emotions": cls.extract_emotions(clean),
            "intensity": cls.infer_intensity(clean),
            "category": cls.classify_category(clean),
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }


class DicionarioPessoal:
    """Dicionário vivo do usuário: aprende a expressão e a intenção."""

    def __init__(self, path: str = "data/dicionario_pessoal.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {"entries": []}
        else:
            self.data = {"entries": []}

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:12]

    def learn(self, text: str, semantics: Dict[str, Any]):
        key = text.strip().lower()
        entry = {
            "hash": self._hash(key),
            "text": text.strip(),
            "semantics": semantics,
            "count": 1,
        }

        existing = False
        for item in self.data["entries"]:
            if item.get("hash") == entry["hash"]:
                item["count"] += 1
                item["semantics"] = semantics
                existing = True
                break
        if not existing:
            self.data["entries"].append(entry)
        self.save()

    def translate(self, text: str) -> Dict[str, Any]:
        q = text.strip().lower()
        for item in self.data["entries"]:
            if item.get("text", "").lower() == q:
                return {
                    "matched": True,
                    "translation": item["semantics"],
                    "hash": item["hash"],
                }
        return {"matched": False, "translation": {"raw": text}, "hash": self._hash(q)}

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


class Arquivista:
    """Memória semântica: nomeação, autenticação, armazenamento e procura."""

    def __init__(self, base_dir: str = "data/arquivista"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                return {"entries": []}
        return {"entries": []}

    def _slug(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug[:60] or "registro"

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def arquivar(self, text: str, semantics: Dict[str, Any]) -> Dict[str, Any]:
        stamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        slug = self._slug(f"{semantics.get('category', 'geral')}-{semantics.get('text', text)[:24]}")
        digest = self._hash_text(text)
        filename = f"{stamp}_{slug}_{digest}.json"
        entry = {
            "filename": filename,
            "timestamp": semantics.get("timestamp_utc", datetime.utcnow().isoformat() + "Z"),
            "hash": digest,
            "text": text,
            "semantics": semantics,
            "category": semantics.get("category", "geral"),
        }
        out = self.base_dir / filename
        out.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        self.index["entries"].append({"filename": filename, "category": entry["category"], "hash": digest})
        self.index_path.write_text(json.dumps(self.index, ensure_ascii=False, indent=2), encoding="utf-8")
        return entry

    def pesquisar(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        matches: List[Dict[str, Any]] = []
        for item in self.index["entries"]:
            if q in item["category"].lower() or q in item["filename"].lower():
                matches.append(item)
        return matches


class GaiaCore:
    """Maestro do ecossistema: junta o XSSRD, dicionário e arquivista."""

    def __init__(self):
        self.xssrd = XSSRD()
        self.dicionario = DicionarioPessoal()
        self.arquivista = Arquivista()

    def process(self, text: str) -> Dict[str, Any]:
        cleaned = self.xssrd.clean(text)
        semantics = self.xssrd.extract_semantics(cleaned)
        self.dicionario.learn(cleaned, semantics)
        entry = self.arquivista.arquivar(cleaned, semantics)

        translated = self.dicionario.translate(cleaned)
        response = {
            "input": text,
            "clean": cleaned,
            "semantics": semantics,
            "entry": entry,
            "dicionario": translated,
            "status": "processed",
        }
        return response


if __name__ == "__main__":
    app = GaiaCore()
    sample = "Eu estava muito cansado depois de trabalhar 12 horas e ainda tinha que cuidar da alimentação porque tenho diabetes tipo 2 e preciso controlar açúcar."
    result = app.process(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\nArquivos salvos em: data/")
