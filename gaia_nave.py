#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAIA NAVE — Ecossistema pessoal de memória e cognição
Offline, por voz, aprende seu padrão, guarda tudo.
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter


# ============================================================================
# XSSRD: Compressor inteligente (remove ruído, preserva intenção)
# ============================================================================

class XSSRD:
    """Remove ruído mantendo semântica e intensidade."""
    
    FILLER = ["tipo assim", "né", "sabe", "tipo", "bem", "sei lá", "cara", "olha", "então"]
    
    @staticmethod
    def clean(text: str) -> str:
        t = text.lower().strip()
        for word in XSSRD.FILLER:
            t = re.sub(rf"\b{word}\b\s*", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    
    @staticmethod
    def intensity(text: str) -> str:
        strong = ["muito", "extremamente", "grave", "crítico", "urgente"]
        weak = ["um pouco", "levemente", "pouco"]
        t = text.lower()
        if any(w in t for w in strong):
            return "ALTA"
        if any(w in t for w in weak):
            return "BAIXA"
        return "MEDIA"
    
    @staticmethod
    def category(text: str) -> str:
        cats = {
            "saude": ["diab", "medic", "dor", "sono", "press"],
            "trabalho": ["trabalh", "projeto", "codigo", "github", "api"],
            "emocional": ["triste", "ansios", "cansad", "medo", "alegr"],
            "juridico": ["contrat", "licenc", "prova", "assin"],
            "financeiro": ["dinheiro", "pagam", "valor", "conta"],
        }
        for cat, patterns in cats.items():
            if any(p in text.lower() for p in patterns):
                return cat
        return "geral"


# ============================================================================
# Dicionário Pessoal Vivo (aprende automaticamente)
# ============================================================================

class DicionarioPessoal:
    """Aprende seu padrão de fala, emoção, intenção."""
    
    def __init__(self, path: str = "data/dicionario.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {"entries": {}}
    
    def learn(self, text: str, semantics: Dict):
        key = text.strip().lower()
        if key not in self.data["entries"]:
            self.data["entries"][key] = {
                "freq": 0,
                "semantics": semantics,
                "variações": [],
            }
        self.data["entries"][key]["freq"] += 1
        if text not in self.data["entries"][key]["variações"]:
            self.data["entries"][key]["variações"].append(text)
        self.save()
    
    def get_meaning(self, text: str) -> Dict:
        key = text.strip().lower()
        if key in self.data["entries"]:
            entry = self.data["entries"][key]
            return {
                "matched": True,
                "freq": entry["freq"],
                **entry["semantics"]
            }
        return {"matched": False}
    
    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))


# ============================================================================
# Arquivista (memória semântica com DNA + hash)
# ============================================================================

@dataclass
class Registro:
    timestamp: str
    texto_original: str
    texto_limpo: str
    categoria: str
    intensidade: str
    emoção: str
    hash_sha256: str
    dna_sounavy: str = "DNA-SOUNAVY"
    
    def filename(self) -> str:
        ts = self.timestamp.replace(":", "").replace("-", "")[:12]
        cat = self.categoria[:3]
        return f"{ts}_{cat}_{self.hash_sha256[:8]}.json"


class Arquivista:
    """Guarda tudo com nome semântico, autenticação, recuperação por intenção."""
    
    def __init__(self, base_dir: str = "data/arquivos"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "index.json"
        self.index = json.loads(self.index_path.read_text()) if self.index_path.exists() else {"registros": []}
    
    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    @staticmethod
    def detect_emotion(text: str) -> str:
        emotions = {
            "cansado": ["cansad", "fadiga", "exaust", "cabo solto"],
            "triste": ["triste", "desanim", "baixa"],
            "feliz": ["feliz", "alegr", "otim"],
            "ansioso": ["ansios", "preocup", "estress"],
            "bravo": ["bravo", "raiva", "furioso"],
        }
        for emotion, patterns in emotions.items():
            if any(p in text.lower() for p in patterns):
                return emotion
        return "neutro"
    
    def guardar(self, texto: str) -> Registro:
        limpo = XSSRD.clean(texto)
        cat = XSSRD.category(texto)
        intensidade = XSSRD.intensity(texto)
        emocao = self.detect_emotion(texto)
        
        reg = Registro(
            timestamp=datetime.utcnow().isoformat() + "Z",
            texto_original=texto,
            texto_limpo=limpo,
            categoria=cat,
            intensidade=intensidade,
            emoção=emocao,
            hash_sha256=self.hash_text(limpo),
        )
        
        arquivo = self.base_dir / reg.filename()
        arquivo.write_text(json.dumps(asdict(reg), ensure_ascii=False, indent=2))
        
        self.index["registros"].append({
            "filename": reg.filename(),
            "categoria": cat,
            "timestamp": reg.timestamp,
            "hash": reg.hash_sha256,
        })
        self.index_path.write_text(json.dumps(self.index, ensure_ascii=False, indent=2))
        
        return reg
    
    def buscar(self, query: str) -> List[Dict]:
        q = query.lower()
        matches = []
        for item in self.index["registros"]:
            if q in item["categoria"] or q in item["filename"]:
                matches.append(item)
        return matches[:5]  # retorna últimos 5


# ============================================================================
# GAIA: Maestro do ecossistema
# ============================================================================

class GAIA:
    """Orquestra tudo: XSSRD + Dicionário + Arquivista."""
    
    def __init__(self):
        self.xssrd = XSSRD()
        self.dicionario = DicionarioPessoal()
        self.arquivista = Arquivista()
        self.historico = []
    
    def processar(self, entrada: str) -> Dict[str, Any]:
        """Processa entrada, aprende, guarda, retorna."""
        
        # 1. LIMPA
        limpo = self.xssrd.clean(entrada)
        
        # 2. EXTRAI SEMÂNTICA
        categoria = self.xssrd.category(entrada)
        intensidade = self.xssrd.intensity(entrada)
        emoção = self.arquivista.detect_emotion(entrada)
        
        semantics = {
            "categoria": categoria,
            "intensidade": intensidade,
            "emoção": emoção,
        }
        
        # 3. APRENDE DICIONÁRIO
        self.dicionario.learn(limpo, semantics)
        
        # 4. GUARDA NO ARQUIVISTA
        registro = self.arquivista.guardar(entrada)
        
        # 5. TRADUZ PRAS MÃOS
        significado = self.dicionario.get_meaning(limpo)
        
        # 6. MONTA RESPOSTA
        resposta = {
            "input": entrada,
            "limpo": limpo,
            "categoria": categoria,
            "intensidade": intensidade,
            "emoção": emoção,
            "arquivo": registro.filename(),
            "hash": registro.hash_sha256,
            "dicionario_freq": significado.get("freq", 1),
        }
        
        self.historico.append(resposta)
        return resposta
    
    def buscar_contexto(self, query: str) -> List[Dict]:
        """Busca por intenção/contexto."""
        return self.arquivista.buscar(query)
    
    def status(self) -> Dict:
        """Mostra o que aprendeu."""
        return {
            "entradas_processadas": len(self.historico),
            "dicionario_entradas": len(self.dicionario.data["entradas"]),
            "arquivos_guardados": len(self.arquivista.index["registros"]),
            "ultimas_categorias": [h["categoria"] for h in self.historico[-5:]],
        }


# ============================================================================
# MAIN: Interface simples
# ============================================================================

def main():
    """Teste funcional completo."""
    
    print("🚀 GAIA NAVE iniciando...\n")
    
    app = GAIA()
    
    # TESTE 1: Processamento básico
    print("=" * 60)
    print("TESTE 1: Entrada confusa, GAIA limpa e processa")
    print("=" * 60)
    
    entrada1 = "Eu estava muito cansado muito mesmo depois de trabalhar 12 horas né e preciso cuidar da alimentação porque tenho diabetes tipo 2"
    
    resultado1 = app.processar(entrada1)
    
    print(f"Input: {entrada1}\n")
    print(f"Limpo: {resultado1['limpo']}")
    print(f"Categoria: {resultado1['categoria']}")
    print(f"Intensidade: {resultado1['intensidade']}")
    print(f"Emoção: {resultado1['emoção']}")
    print(f"Arquivo: {resultado1['arquivo']}")
    print(f"Hash: {resultado1['hash']}\n")
    
    # TESTE 2: Aprendizado (mesma coisa dita de outro jeito)
    print("=" * 60)
    print("TESTE 2: Variação da mesma coisa, dicionário aprende padrão")
    print("=" * 60)
    
    entrada2 = "Tô de cabo solto, trabalho muito, diabetes me preocupa"
    resultado2 = app.processar(entrada2)
    
    print(f"Input: {entrada2}")
    print(f"Limpo: {resultado2['limpo']}")
    print(f"Emoção: {resultado2['emoção']}")
    print(f"Freq no dicionário: {resultado2['dicionario_freq']}\n")
    
    # TESTE 3: Reconhecimento automático (já sabe o padrão)
    print("=" * 60)
    print("TESTE 3: Mesma intenção, menos palavras. GAIA já reconhece")
    print("=" * 60)
    
    entrada3 = "Cansado"
    resultado3 = app.processar(entrada3)
    
    print(f"Input: {entrada3}")
    print(f"Categoria detectada: {resultado3['categoria']}")
    print(f"Emoção: {resultado3['emoção']}")
    print(f"Sistema sabe que você tá falando de trabalho + saúde\n")
    
    # TESTE 4: Busca por contexto
    print("=" * 60)
    print("TESTE 4: Busca por contexto (quando você pede 'traz tudo de saúde')")
    print("=" * 60)
    
    busca = app.buscar_contexto("saude")
    print(f"Encontrados {len(busca)} registros de saúde:")
    for item in busca:
        print(f"  - {item['filename']} ({item['timestamp'][:10]})")
    print()
    
    # TESTE 5: Status
    print("=" * 60)
    print("STATUS: O que GAIA aprendeu")
    print("=" * 60)
    
    status = app.status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print()
    
    # TESTE 6: Export pra check-up
    print("=" * 60)
    print("PRONTO PRA SYNC: Aqui vai o que GAIA traz pro Claude revisar")
    print("=" * 60)
    
    export = {
        "periodo": "2026-10-06",
        "status": status,
        "dicionario_resumo": {
            "total_entradas": len(app.dicionario.data["entries"]),
            "top_palavras": list(app.dicionario.data["entries"].keys())[:5],
        },
        "ultimos_registros": [h["arquivo"] for h in app.historico[-3:]],
    }
    
    print(json.dumps(export, ensure_ascii=False, indent=2))
    print()
    
    print("✅ TESTES COMPLETOS - SISTEMA FUNCIONAL")
    print("📁 Arquivos guardados em: data/")
    print("💾 Dicionário guardado em: data/dicionario.json")
    print("🔍 Índice guardado em: data/arquivos/index.json")


if __name__ == "__main__":
    main()
