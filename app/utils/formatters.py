import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Union


def format_currency(cents: Union[int, float, Decimal, None]) -> str:
    """Converte centavos inteiros para formato monetário brasileiro R$ 0,00."""
    if cents is None:
        cents = 0
    if not isinstance(cents, int):
        cents = int(round(float(cents)))
    
    is_negative = cents < 0
    cents_abs = abs(cents)
    reais = cents_abs // 100
    resto = cents_abs % 100
    
    # Formatação com separador de milhar por ponto e decimal por vírgula
    reais_str = f"{reais:,}".replace(",", ".")
    result = f"R$ {reais_str},{resto:02d}"
    return f"-{result}" if is_negative else result


def parse_currency_to_cents(value: Union[str, int, float, Decimal, None]) -> int:
    """
    Converte qualquer entrada (str, float, int, Decimal) em centavos inteiros.
    Aceita: "15,50", "R$ 1.250,50", "1250.50", 15.5, 1550.
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        return int(round(float(value) * 100))
    
    # Se for string
    clean_val = str(value).strip().replace("R$", "").replace("r$", "").strip()
    if not clean_val:
        return 0
    
    # Remove espaços
    clean_val = clean_val.replace(" ", "")
    
    # Trata formato brasileiro (1.234,56) vs internacional (1234.56)
    if "," in clean_val and "." in clean_val:
        # Ex: 1.250,50 -> remove ponto, troca vírgula por ponto
        clean_val = clean_val.replace(".", "").replace(",", ".")
    elif "," in clean_val:
        clean_val = clean_val.replace(",", ".")
        
    try:
        dec = Decimal(clean_val)
        return int(round(dec * 100))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Valor monetário inválido: '{value}'")


def format_date(val: Union[date, datetime, str, None]) -> str:
    """Converte date/datetime para DD/MM/AAAA."""
    if not val:
        return "-"
    if isinstance(val, (date, datetime)):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, str):
        try:
            # Tenta parsing ISO
            dt = datetime.fromisoformat(val)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return val
    return str(val)


def format_datetime(val: Union[datetime, str, None]) -> str:
    """Converte datetime para DD/MM/AAAA às HH:MM."""
    if not val:
        return "-"
    if isinstance(val, datetime):
        return val.strftime("%d/%m/%Y às %H:%M")
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val)
            return dt.strftime("%d/%m/%Y às %H:%M")
        except ValueError:
            return val
    return str(val)


def clean_digits(val: Optional[str]) -> str:
    """Extrai somente os dígitos numéricos de uma string."""
    if not val:
        return ""
    return re.sub(r"\D", "", val)


def format_cpf(cpf: Optional[str]) -> str:
    """Formata CPF: 12345678901 -> 123.456.789-01."""
    digits = clean_digits(cpf)
    if len(digits) != 11:
        return cpf or ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def format_phone(phone: Optional[str]) -> str:
    """Formata telefone: (11) 98765-4321 ou (11) 3456-7890."""
    digits = clean_digits(phone)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return phone or ""
