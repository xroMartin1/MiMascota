"""Datos de contacto privados y selección explícita de datos para la chapa."""
import re


def contact_values(values, required=False):
    result = {key: str(values.get(key, "")).strip() for key in ("name", "phone", "city")}
    if required and not result["name"]:
        raise ValueError("Escribe el nombre de la persona de contacto.")
    if len(result["name"]) > 60 or len(result["city"]) > 80:
        raise ValueError("Usa un nombre de hasta 60 caracteres y una comuna de hasta 80.")
    if result["phone"]:
        phone = re.sub(r"[\s().-]", "", result["phone"])
        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
            raise ValueError("Incluye el código de país. Ejemplo: +56 9 1234 5678.")
        result["phone"] = phone
    elif required:
        raise ValueError("Añade un teléfono para que puedan contactar contigo.")
    return result


def registration_values(values):
    if not values.get('name', '').strip():
        raise ValueError('Escribe tu nombre.')
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]):
        raise ValueError("Escribe un correo válido.")
    if len(values["password"]) < 8:
        raise ValueError("Usa una contraseña de al menos 8 caracteres.")
    if values["password"] != values["password_confirm"]:
        raise ValueError("Las contraseñas no coinciden.")
    return contact_values(values, required=False)
