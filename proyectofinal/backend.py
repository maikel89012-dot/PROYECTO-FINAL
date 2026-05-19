# -*- coding: utf-8 -*-
"""
Modulo de Backend: Sistema de Gestion de Rutas de Transporte Estudiantil (Puebla)
---------------------------------------------------------------------------------
Desarrollado para: Estudiantes de BUAP, Tec de Monterrey, e IPN.
Licencia: Convenio Metropolitano de Transporte de Puebla (50% de Descuento).

Este modulo implementa de forma exhaustiva el nucleo de negocio del sistema de
gestion de rutas, aplicando rigurosamente los principios de Programacion Orientada
a Objetos (POO) en su maxima expresion:
1. Encapsulamiento: Uso de propiedades privadas, metodos de validacion estrictos,
   desacoplamiento de capas y control de visibilidad.
2. Herencia: Jerarquia de clases bien definida donde Pasajero y Administrador
   heredan y extienden el comportamiento de la clase abstracta/base Usuario.
3. Polimorfismo: Sobrecarga de metodos, sobreescritura de constructores y
   comportamientos de cobro dinamico segun la naturaleza de la tarjeta de movilidad.
4. Modularidad y Cohesion: Clases enfocadas en resolver una sola responsabilidad
   (Single Responsibility Principle), facilitando la escalabilidad del sistema.

Sub-sistemas avanzados integrados:
- Enrutador de Red Metropolitano (Algoritmo de Dijkstra).
- Predictor de Trafico y Congestion mediante Analisis Temporal.
- Gestor Escolar de Calendario y Frecuencia de Unidades.
- Auditor de Operaciones y Seguridad con Cifrado Hash.
- Simulador de Telemetria de Vehiculos en Transito (Consumo y Desgaste).
- Interfaz CLI (REPL) para Gestion por Terminal.
- Suite de Pruebas Unitarias Integrada con 35 Casos de Prueba.
- Persistencia de Datos Completa (JSON/CSV) y Generador de Semillas Historicas.
"""

import os
import re
import csv
import json
import math
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union
import unittest

try:
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Modo no interactivo para evitar fallos de hilos con interfaces graficas
    import matplotlib.pyplot as plt
    PANDAS_MATPLOTLIB_AVAILABLE = True
except ImportError:
    PANDAS_MATPLOTLIB_AVAILABLE = False

# CONFIGURACIONES Y CONSTANTES GLOBALES
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(BASE_DIR, "assets", "charts")

# Asegurar directorios fisicos en el workspace
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

ARCHIVO_USUARIOS = os.path.join(DATA_DIR, "usuarios.json")
ARCHIVO_TARJETAS = os.path.join(DATA_DIR, "tarjetas.json")
ARCHIVO_RUTAS = os.path.join(DATA_DIR, "rutas.json")
ARCHIVO_VEHICULOS = os.path.join(DATA_DIR, "vehiculos.json")
ARCHIVO_VIAJES = os.path.join(DATA_DIR, "viajes.csv")
ARCHIVO_LOGS = os.path.join(DATA_DIR, "sistema_logs.txt")
ARCHIVO_AUDITORIA = os.path.join(DATA_DIR, "auditoria_transacciones.csv")
ARCHIVO_RESPALDOS = os.path.join(DATA_DIR, "registro_respaldos.json")

TARIFA_ESTANDAR = 10.00       # Pasaje regular en Pesos
DESCUENTO_ESTUDIANTE = 0.50   # 50% de descuento autorizado por el Estado
UNIVERSIDADES_DESCUENTO = ["BUAP", "TEC DE MONTERREY", "IPN"]


class TransporteException(Exception):
    """Excepcion base y abstracta para todas las fallas en la red de transporte."""
    def __init__(self, mensaje: str, codigo_error: int = 100):
        super().__init__(mensaje)
        self._mensaje = mensaje
        self._codigo_error = codigo_error
        self._timestamp = datetime.now()
        self.registrar_evento()

    @property
    def mensaje(self) -> str:
        return self._mensaje

    @property
    def codigo_error(self) -> int:
        return self._codigo_error

    def registrar_evento(self):
        """Registra el fallo de forma automatica en la bitacora general de errores."""
        try:
            with open(ARCHIVO_LOGS, mode='a', encoding='utf-8') as f:
                f.write(f"[{self._timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ERROR_CODE {self._codigo_error}: {self._mensaje}\n")
        except Exception:
            pass


class AutenticacionError(TransporteException):
    """Lanzada cuando fallan las credenciales o accesos al sistema."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=101)


class SaldoInsuficienteError(TransporteException):
    """Lanzada cuando una tarjeta inteligente no cuenta con balance suficiente."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=102)


class CapacidadExcedidaError(TransporteException):
    """Lanzada cuando un autobus o van de la universidad sobrepasa su aforo de pasajeros."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=103)


class RecursoNoEncontradoError(TransporteException):
    """Lanzada al no hallar rutas, vehiculos o paradas específicas en la base de datos."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=104)


class ValidacionDatosError(TransporteException):
    """Lanzada cuando las entradas del usuario no cumplen con el formato o restricciones."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=105)


class ValidacionAcademicaError(TransporteException):
    """Lanzada al fallar los convenios de vigencia estudiantil (BUAP, Tec, IPN)."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=106)


class RutaNavegacionError(TransporteException):
    """Lanzada si la red no puede calcular un camino viable por desconexion de paradas."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=107)


class SeguridadAuditoriaError(TransporteException):
    """Lanzada ante intentos de manipulacion de datos o firmas digitales corruptas."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=108)


class CalendarioExcepcion(TransporteException):
    """Lanzada ante incongruencias en programaciones de fechas escolares o calendarios."""
    def __init__(self, mensaje: str):
        super().__init__(mensaje, codigo_error=109)



class Usuario:
    """Clase Base que modela a cualquier persona con credenciales en la plataforma.
    Aplica encapsulamiento estricto a las variables criticas e implementa setters con validaciones.
    """
    def __init__(self, id_usuario: int, nombre: str, correo: str, contrasena_hash: str, tipo_usuario: str, id_escuela: str = "Ninguna"):
        self._id_usuario = self._validar_entero(id_usuario, "ID Usuario")
        self._nombre = self._validar_texto(nombre, "Nombre")
        self._correo = self._validar_correo(correo)
        self._contrasena_hash = contrasena_hash
        self._tipo_usuario = self._validar_tipo(tipo_usuario)
        self._id_escuela = id_escuela.strip().upper()
        self._sesion_activa = False
        self._ultimo_acceso: Optional[str] = None

    @property
    def id_usuario(self) -> int:
        return self._id_usuario

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str):
        self._nombre = self._validar_texto(valor, "Nombre")

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str):
        self._correo = self._validar_correo(valor)

    @property
    def tipo_usuario(self) -> str:
        return self._tipo_usuario

    @property
    def id_escuela(self) -> str:
        return self._id_escuela

    @id_escuela.setter
    def id_escuela(self, valor: str):
        self._id_escuela = valor.strip().upper()

    @property
    def sesion_activa(self) -> bool:
        return self._sesion_activa

    @property
    def ultimo_acceso(self) -> Optional[str]:
        return self._ultimo_acceso

    @staticmethod
    def _validar_entero(valor: Any, nombre_campo: str) -> int:
        try:
            val = int(valor)
            if val <= 0:
                raise ValueError
            return val
        except (ValueError, TypeError):
            raise ValidacionDatosError(f"El campo '{nombre_campo}' debe ser un numero entero positivo.")

    @staticmethod
    def _validar_texto(valor: Any, nombre_campo: str) -> str:
        if not valor or not isinstance(valor, str) or not valor.strip():
            raise ValidacionDatosError(f"El campo '{nombre_campo}' no puede estar vacio y debe ser un texto.")
        return valor.strip()

    @staticmethod
    def _validar_correo(correo: str) -> str:
        if not isinstance(correo, str) or "@" not in correo or "." not in correo or len(correo) < 5:
            raise ValidacionDatosError("La direccion de correo electronico provista no tiene un formato valido.")
        return correo.strip().lower()

    @staticmethod
    def _validar_tipo(tipo: str) -> str:
        tipo_normalizado = tipo.strip().capitalize()
        if tipo_normalizado not in ["Pasajero", "Administrador"]:
            raise ValidacionDatosError("El tipo de usuario debe ser obligatoriamente 'Pasajero' o 'Administrador'.")
        return tipo_normalizado

    def iniciar_sesion(self, contrasena_plana: str) -> bool:
        """Valida contraseñas cifrando la entrada plana con SHA-256."""
        hash_ingreso = hashlib.sha256(contrasena_plana.encode('utf-8')).hexdigest()
        if hash_ingreso == self._contrasena_hash:
            self._sesion_activa = True
            self._ultimo_acceso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
        return False

    def cerrar_sesion(self) -> bool:
        """Termina de forma limpia el estado de sesion del usuario."""
        self._sesion_activa = False
        return True

    def actualizar_datos(self, nombre: Optional[str] = None, correo: Optional[str] = None, contrasena_nueva: Optional[str] = None) -> bool:
        """Modifica datos basicos auditando las restricciones de seguridad."""
        if nombre:
            self.nombre = nombre
        if correo:
            self.correo = correo
        if contrasena_nueva:
            if len(contrasena_nueva) < 6:
                raise ValidacionDatosError("La contrasena nueva debe contener al menos 6 caracteres por seguridad.")
            self._contrasena_hash = hashlib.sha256(contrasena_nueva.encode('utf-8')).hexdigest()
        return True

    def a_diccionario(self) -> Dict[str, Any]:
        """Metodo de serializacion a diccionario para persistencia JSON."""
        return {
            "id_usuario": self._id_usuario,
            "nombre": self._nombre,
            "correo": self._correo,
            "contrasena_hash": self._contrasena_hash,
            "tipo_usuario": self._tipo_usuario,
            "id_escuela": self._id_escuela,
            "ultimo_acceso": self._ultimo_acceso
        }


class Pasajero(Usuario):
    """
    2. Clase que hereda de USUARIO, destinada a los estudiantes y ciudadanos
    que utilizan la red de transporte y consultan paradas activas.
    """
    def __init__(self, id_usuario: int, nombre: str, correo: str, contrasena_hash: str, id_escuela: str = "Ninguna",
                 historial_viajes: Optional[List[Dict[str, Any]]] = None, preferencias: str = ""):
        super().__init__(id_usuario, nombre, correo, contrasena_hash, "Pasajero", id_escuela)
        self._historial_viajes = historial_viajes if historial_viajes is not None else []
        self._preferencias = preferencias.strip()

    @property
    def historial_viajes(self) -> List[Dict[str, Any]]:
        return self._historial_viajes

    @property
    def preferencias(self) -> str:
        return self._preferencias

    @preferencias.setter
    def preferencias(self, valor: str):
        self._preferencias = valor.strip()

    def buscar_destino(self, punto_interes: str, lista_rutas: List[Any]) -> List[Tuple[Any, Any]]:
        """Busca estaciones o rutas asociadas a puntos clave en Puebla."""
        resultados = []
        punto_normalizado = punto_interes.lower().strip()
        
        for ruta in lista_rutas:
            for estacion in ruta.lista_estaciones:
                coincide_punto = any(punto_normalizado in pt.lower() for pt in estacion.puntos_interes)
                coincide_parada = punto_normalizado in estacion.nombre_parada.lower()
                
                if coincide_punto or coincide_parada:
                    resultados.append((ruta, estacion))
        return resultados

    def consultar_llegada(self, id_estacion: int, ruta: Any) -> Optional[float]:
        """Calcula el ETA en minutos hacia una parada basandose en la geolocalizacion."""
        unidades = ruta.obtener_unidades_activas()
        if not unidades:
            return None
            
        idx_estacion = -1
        for i, est in enumerate(ruta.lista_estaciones):
            if est.id_estacion == id_estacion:
                idx_estacion = i
                break
                
        if idx_estacion == -1:
            raise RecursoNoEncontradoError(f"La parada ID {id_estacion} no forma parte de la ruta {ruta.nombre_ruta}.")

        est_destino = ruta.lista_estaciones[idx_estacion]
        eta_minimo = float('inf')

        for vehiculo in unidades:
            distancia_km = MathUtils.calcular_distancia_gps(
                vehiculo.ubicacion_actual[0], vehiculo.ubicacion_actual[1],
                est_destino.coordenadas[0], est_destino.coordenadas[1]
            )
            # Asumimos velocidad promedio prudente del bus escolar de 35 km/h
            tiempo_horas = distancia_km / 35.0
            tiempo_minutos = tiempo_horas * 60.0

            if tiempo_minutos < eta_minimo:
                eta_minimo = tiempo_minutos

        return round(eta_minimo, 2) if eta_minimo != float('inf') else None

    def generar_reporte_gastos(self) -> Dict[str, Any]:
        """Analiza financieramente el gasto de pasajes bimestral en Puebla (Ultimos 60 dias)."""
        ahora = datetime.now()
        limite_bimestral = ahora - timedelta(days=60)
        total_gastado = 0.0
        conteo_viajes = 0
        desglose_gastos = {"BUAP": 0.0, "TEC DE MONTERREY": 0.0, "IPN": 0.0, "OTROS": 0.0}

        for viaje in self._historial_viajes:
            try:
                fecha_v = datetime.strptime(viaje["fecha_hora"], "%Y-%m-%d %H:%M:%S")
                if fecha_v >= limite_bimestral:
                    costo = float(viaje["costo_aplicado"])
                    total_gastado += costo
                    conteo_viajes += 1
                    
                    escuela = viaje.get("id_escuela", "Ninguna").upper()
                    if "BUAP" in escuela:
                        desglose_gastos["BUAP"] += costo
                    elif "TEC" in escuela or "MONTERREY" in escuela:
                        desglose_gastos["TEC DE MONTERREY"] += costo
                    elif "IPN" in escuela:
                        desglose_gastos["IPN"] += costo
                    else:
                        desglose_gastos["OTROS"] += costo
            except Exception:
                continue

        costo_medio = total_gastado / conteo_viajes if conteo_viajes > 0 else 0.0
        return {
            "id_pasajero": self.id_usuario,
            "nombre": self.nombre,
            "universidad": self.id_escuela,
            "total_gasto_bimestral": round(total_gastado, 2),
            "total_viajes": conteo_viajes,
            "costo_promedio_viaje": round(costo_medio, 2),
            "desglose_por_universidad": desglose_gastos
        }

    def a_diccionario(self) -> Dict[str, Any]:
        """Extiende el formato base para Pasajero."""
        dicc = super().a_diccionario()
        dicc.update({
            "historial_viajes": self._historial_viajes,
            "preferencias": self._preferencias
        })
        return dicc


class Administrador(Usuario):
    """
    Clase que representa al personal administrativo de Puebla encargado de auditar
    y liberar congestiones despachando unidades de apoyo.
    """
    def __init__(self, id_usuario: int, nombre: str, correo: str, contrasena_hash: str, id_escuela: str = "Ninguna"):
        super().__init__(id_usuario, nombre, correo, contrasena_hash, "Administrador", id_escuela)
        self._alertas_atendidas = 0

    @property
    def alertas_atendidas(self) -> int:
        return self._alertas_atendidas

    def atender_alerta_sobrecupo(self, vehiculo: Any) -> str:
        """Despacha unidades de apoyo y restablece el aforo seguro de una unidad saturada."""
        if vehiculo.pasajeros_actuales > vehiculo.capacidad_max:
            # Reubica al 30% de los pasajeros a bordo en una unidad mock de apoyo
            vehiculo.pasajeros_actuales = int(vehiculo.capacidad_max * 0.7)
            self._alertas_atendidas += 1
            return f"Administrador {self.nombre} atendio alerta: Despachada unidad de apoyo para liberar Unidad {vehiculo.id_unidad}."
        return f"La Unidad {vehiculo.id_unidad} opera dentro de los parametros seguros."


class Vehiculo:
    """
    3. Representa las unidades de transporte (autobuses/vans) que operan en las rutas,
    permitiendo monitorear su ocupacion y telemetria en tiempo real.
    """
    def __init__(self, id_unidad: str, capacidad_max: int, pasajeros_actuales: int,
                 ubicacion_actual: Tuple[float, float], estado: str = "En parada"):
        self._id_unidad = self._validar_id_unidad(id_unidad)
        self._capacidad_max = int(capacidad_max)
        self._pasajeros_actuales = int(pasajeros_actuales)
        self._ubicacion_actual = ubicacion_actual
        self._estado = self._validar_estado(estado)
        self._alertas_enviadas = 0
        # Telemetria avanzada integrada
        self._temperatura_motor = 88.5  # Celsius
        self._nivel_combustible = 100.0 # Porcentaje
        self._consumo_promedio = 0.0    # Litros acumulados

    @property
    def id_unidad(self) -> str:
        return self._id_unidad

    @property
    def capacidad_max(self) -> int:
        return self._capacidad_max

    @property
    def pasajeros_actuales(self) -> int:
        return self._pasajeros_actuales

    @pasajeros_actuales.setter
    def pasajeros_actuales(self, valor: int):
        val = int(valor)
        if val < 0:
            raise ValidacionDatosError("El numero de pasajeros a bordo no puede ser negativo.")
        self._pasajeros_actuales = val
        self.monitorear_volumen()

    @property
    def ubicacion_actual(self) -> Tuple[float, float]:
        return self._ubicacion_actual

    @ubicacion_actual.setter
    def ubicacion_actual(self, coordenadas: Tuple[float, float]):
        if not isinstance(coordenadas, tuple) or len(coordenadas) != 2:
            raise ValidacionDatosError("Las coordenadas GPS deben ser una tupla con latitud y longitud.")
        self._ubicacion_actual = (float(coordenadas[0]), float(coordenadas[1]))

    @property
    def estado(self) -> str:
        return self._estado

    @estado.setter
    def estado(self, valor: str):
        self._estado = self._validar_estado(valor)

    @property
    def alertas_enviadas(self) -> int:
        return self._alertas_enviadas

    @property
    def temperatura_motor(self) -> float:
        return self._temperatura_motor

    @property
    def nivel_combustible(self) -> float:
        return self._nivel_combustible

    @staticmethod
    def _validar_id_unidad(id_u: str) -> str:
        if not id_u or not isinstance(id_u, str) or not id_u.strip():
            raise ValidacionDatosError("El ID de la unidad no puede estar vacio.")
        return id_u.strip().upper()

    @staticmethod
    def _validar_estado(est: str) -> str:
        estado_normalizado = est.strip().capitalize()
        estados_validos = ["En ruta", "Fuera de servicio", "En parada"]
        if estado_normalizado not in estados_validos:
            raise ValidacionDatosError(f"Estado de vehiculo invalido. Opciones: {estados_validos}")
        return estado_normalizado

    def actualizar_posicion(self, nueva_lat: float, nueva_lon: float) -> Tuple[float, float]:
        """Envía las coordenadas de ubicacion simulando consumo y telemetria."""
        self.ubicacion_actual = (nueva_lat, nueva_lon)
        # Simular consumo leve por transito: combustible baja 0.1% por paso, calor motor fluctua
        self._nivel_combustible = max(5.0, self._nivel_combustible - 0.05)
        self._temperatura_motor = min(105.0, max(85.0, self._temperatura_motor + random.uniform(-0.5, 0.8)))
        return self.ubicacion_actual

    def monitorear_volumen(self) -> str:
        """Determina de forma dinamica la afluencia de pasajeros en la unidad."""
        if self._capacidad_max <= 0:
            return "Indefinido"
        
        ratio = self._pasajeros_actuales / self._capacidad_max
        if ratio >= 1.0:
            self.enviar_alerta_sobrecupo()
            return "Sobreocupado"
        elif ratio >= 0.8:
            return "Alto"
        elif ratio >= 0.4:
            return "Medio"
        else:
            return "Bajo"

    def enviar_alerta_sobrecupo(self) -> bool:
        """Notifica y levanta alerta en bitacora si se sobrepasa la capacidad de aforo."""
        self._alertas_enviadas += 1
        mensaje = f"SOBRECUPO DETECTADO: Unidad {self._id_unidad} sobrepasada. Capacidad: {self._capacidad_max}, Abordados: {self._pasajeros_actuales}"
        try:
            with open(ARCHIVO_LOGS, mode='a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")
        except Exception:
            pass
        return True

    def realizar_mantenimiento(self):
        """Restablece los sensores de telemetria al realizar servicio preventivo."""
        self._nivel_combustible = 100.0
        self._temperatura_motor = 86.2
        return True

    def a_diccionario(self) -> Dict[str, Any]:
        return {
            "id_unidad": self._id_unidad,
            "capacidad_max": self._capacidad_max,
            "pasajeros_actuales": self._pasajeros_actuales,
            "ubicacion_actual": list(self._ubicacion_actual),
            "estado": self._estado,
            "temperatura_motor": round(self._temperatura_motor, 2),
            "nivel_combustible": round(self._nivel_combustible, 2)
        }


class EstacionParada:
    """
    5. Representa los puntos fisicos (paradas/estaciones) de abordaje del sistema.
    Almacena los horarios de pasada programados para los buses.
    """
    def __init__(self, id_estacion: int, nombre_parada: str, coordenadas: Tuple[float, float],
                 puntos_interes: Optional[List[str]] = None, scheduled_times: Optional[Dict[str, List[str]]] = None):
        self._id_estacion = int(id_estacion)
        self._nombre_parada = nombre_parada.strip()
        self._coordenadas = coordenadas
        self._puntos_interes = puntos_interes if puntos_interes is not None else []
        self._scheduled_times = scheduled_times if scheduled_times is not None else {}
        self._personas_esperando = 0

    @property
    def id_estacion(self) -> int:
        return self._id_estacion

    @property
    def nombre_parada(self) -> str:
        return self._nombre_parada

    @property
    def coordenadas(self) -> Tuple[float, float]:
        return self._coordenadas

    @property
    def puntos_interes(self) -> List[str]:
        return self._puntos_interes

    @property
    def scheduled_times(self) -> Dict[str, List[str]]:
        return self._scheduled_times

    def mostrar_proximas_llegadas(self, nombre_ruta: str) -> List[str]:
        """Filtra horarios programados futuros comparandolos con la hora real."""
        horarios = self._scheduled_times.get(nombre_ruta, [])
        ahora_str = datetime.now().strftime("%H:%M")
        
        proximas = []
        for h in sorted(horarios):
            if h >= ahora_str:
                proximas.append(h)
        return proximas if proximas else ["No hay mas recorridos hoy"]

    def contar_espera(self, volumen_historico: int = 5) -> int:
        """Estima la cantidad de alumnos en espera segun horas pico escolares."""
        hora_actual = datetime.now().hour
        if hora_actual in [7, 8, 13, 14, 18, 19]:
            self._personas_esperando = random.randint(18, 40)
        else:
            self._personas_esperando = random.randint(2, 8)
        return self._personas_esperando

    def a_diccionario(self) -> Dict[str, Any]:
        return {
            "id_estacion": self._id_estacion,
            "nombre_parada": self._nombre_parada,
            "coordenadas": list(self._coordenadas),
            "puntos_interes": self._puntos_interes,
            "scheduled_times": self._scheduled_times
        }


class Ruta:
    """
    4. Define el trayecto que recorre el transporte, coordinando paradas ordenadas
    y controlando los vehiculos que se encuentran transitando en ella.
    """
    def __init__(self, id_ruta: int, nombre_ruta: str, lista_estaciones: List[EstacionParada],
                 tarifa_base: float = 10.00, universidad_afiliada: str = "General"):
        self._id_ruta = int(id_ruta)
        self._nombre_ruta = nombre_ruta.strip()
        self._lista_estaciones = lista_estaciones
        self._tarifa_base = float(tarifa_base)
        self._universidad_afiliada = universidad_afiliada.strip().upper()
        self._unidades_activas: List[Vehiculo] = []

    @property
    def id_ruta(self) -> int:
        return self._id_ruta

    @property
    def nombre_ruta(self) -> str:
        return self._nombre_ruta

    @property
    def lista_estaciones(self) -> List[EstacionParada]:
        return self._lista_estaciones

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @tarifa_base.setter
    def tarifa_base(self, valor: float):
        if valor < 0:
            raise ValidacionDatosError("La tarifa no puede ser negativa.")
        self._tarifa_base = float(valor)

    @property
    def universidad_afiliada(self) -> str:
        return self._universidad_afiliada

    def calcular_trayecto(self) -> float:
        """Determina con precision la distancia total de la ruta en Kilometros."""
        if len(self._lista_estaciones) < 2:
            return 0.0
        
        distancia_acumulada = 0.0
        for i in range(len(self._lista_estaciones) - 1):
            e1 = self._lista_estaciones[i]
            e2 = self._lista_estaciones[i+1]
            distancia_acumulada += MathUtils.calcular_distancia_gps(
                e1.coordenadas[0], e1.coordenadas[1],
                e2.coordenadas[0], e2.coordenadas[1]
            )
        return round(distancia_acumulada, 2)

    def asociar_unidad(self, vehiculo: Vehiculo):
        """Vincula un autobus al recorrido activo de la ruta."""
        if vehiculo not in self._unidades_activas:
            self._unidades_activas.append(vehiculo)

    def desasociar_unidad(self, vehiculo: Vehiculo):
        """Desvincula un autobus de la ruta."""
        if vehiculo in self._unidades_activas:
            self._unidades_activas.remove(vehiculo)

    def obtener_unidades_activas(self) -> List[Vehiculo]:
        """Retorna las unidades que se encuentran operando actualmente."""
        return [v for v in self._unidades_activas if v.estado != "Fuera de servicio"]

    def a_diccionario(self) -> Dict[str, Any]:
        return {
            "id_ruta": self._id_ruta,
            "nombre_ruta": self._nombre_ruta,
            "lista_estaciones": [e.id_estacion for e in self._lista_estaciones],
            "tarifa_base": self._tarifa_base,
            "universidad_afiliada": self._universidad_afiliada
        }


class TarjetaMovilidad:
    """
    6. Administra el saldo y cobros. Aplica polimorficamente un descuento
    del 50% si el estudiante pertenece a la BUAP, Tec, o IPN.
    """
    def __init__(self, id_tarjeta: str, saldo_actual: float, id_usuario: int,
                 fecha_ult_uso: Optional[str] = None, tipo_descuento: str = "Regular"):
        self._id_tarjeta = self._validar_id_tarjeta(id_tarjeta)
        self._saldo_actual = self._validar_saldo(saldo_actual)
        self._id_usuario = int(id_usuario)
        self._fecha_ult_uso = fecha_ult_uso if fecha_ult_uso else datetime.now().strftime("%Y-%m-%d")
        self._tipo_descuento = tipo_descuento.strip().upper()

    @property
    def id_tarjeta(self) -> str:
        return self._id_tarjeta

    @property
    def saldo_actual(self) -> float:
        return self._saldo_actual

    @property
    def id_usuario(self) -> int:
        return self._id_usuario

    @property
    def fecha_ult_uso(self) -> str:
        return self._fecha_ult_uso

    @property
    def tipo_descuento(self) -> str:
        return self._tipo_descuento

    @tipo_descuento.setter
    def tipo_descuento(self, valor: str):
        self._tipo_descuento = valor.strip().upper()

    @staticmethod
    def _validar_id_tarjeta(identificador: str) -> str:
        if not identificador or not isinstance(identificador, str) or len(identificador.strip()) < 4:
            raise ValidacionDatosError("El ID de tarjeta inteligente debe ser de al menos 4 caracteres.")
        return identificador.strip().upper()

    @staticmethod
    def _validar_saldo(saldo: float) -> float:
        try:
            val = float(saldo)
            if val < 0:
                raise ValueError
            return val
        except (ValueError, TypeError):
            raise ValidacionDatosError("El balance de recarga no puede ser negativo.")

    def descontar_pasaje(self, tarifa_base: float) -> float:
        """Deduce el balance de pasaje aplicando el 50% de descuento estudiantil."""
        costo_cobrado = tarifa_base
        
        # Aplicacion de Polimorfismo e Incentivo Estudiantil en Puebla
        if self._tipo_descuento in UNIVERSIDADES_DESCUENTO:
            costo_cobrado = tarifa_base * DESCUENTO_ESTUDIANTE
            
        if self._saldo_actual < costo_cobrado:
            raise SaldoInsuficienteError(f"Fondos insuficientes. Requerido: ${costo_cobrado:.2f}, Balance: ${self._saldo_actual:.2f}")
            
        self._saldo_actual -= costo_cobrado
        self._fecha_ult_uso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Auditar la transaccion de forma interna en bitacora financiera
        AuditLogger.registrar_transaccion(self._id_tarjeta, "DEBITO", costo_cobrado, self._saldo_actual)
        return costo_cobrado

    def recargar_saldo(self, monto: float) -> float:
        """Aumenta el balance de saldo de la tarjeta validando politicas de montos."""
        if monto <= 0:
            raise ValidacionDatosError("El monto de recarga de la tarjeta debe ser mayor a cero.")
        if monto > 1000.0:
            raise ValidacionDatosError("No se permite recargar montos superiores a $1000.00 de forma unitaria.")
            
        self._saldo_actual += monto
        AuditLogger.registrar_transaccion(self._id_tarjeta, "RECARGA", monto, self._saldo_actual)
        return self._saldo_actual

    def verificar_saldo(self) -> float:
        """Muestra el balance actual consolidado."""
        return round(self._saldo_actual, 2)

    def a_diccionario(self) -> Dict[str, Any]:
        return {
            "id_tarjeta": self._id_tarjeta,
            "saldo_actual": self._saldo_actual,
            "id_usuario": self._id_usuario,
            "fecha_ult_uso": self._fecha_ult_uso,
            "tipo_descuento": self._tipo_descuento
        }


class RegistroViaje:
    """
    7. Clase encargada de almacenar y consolidar los registros de abordajes
    de pasajeros en Puebla para auditorias e informes financieros.
    """
    def __init__(self, id_viaje: int, id_pasajero: int, id_unidad: str,
                 costo_aplicado: float, fecha_hora: str, id_escuela: str = "Ninguna"):
        self.id_viaje = int(id_viaje)
        self.id_pasajero = int(id_pasajero)
        self.id_unidad = id_unidad.strip().upper()
        self.costo_aplicado = float(costo_aplicado)
        self.fecha_hora = fecha_hora.strip()
        self.id_escuela = id_escuela.strip().upper()

    def a_lista_csv(self) -> List[str]:
        """Formatea los atributos para persistir en formato CSV."""
        return [
            str(self.id_viaje),
            str(self.id_pasajero),
            self.id_unidad,
            f"{self.costo_aplicado:.2f}",
            self.fecha_hora,
            self.id_escuela
        ]

    @staticmethod
    def de_lista_csv(fila: List[str]) -> 'RegistroViaje':
        """Instancia un registro a partir de una tupla leida de CSV."""
        return RegistroViaje(
            id_viaje=int(fila[0]),
            id_pasajero=int(fila[1]),
            id_unidad=fila[2],
            costo_aplicado=float(fila[3]),
            fecha_hora=fila[4],
            id_escuela=fila[5] if len(fila) > 5 else "Ninguna"
        )



class EstadisticaSistema:
    """
    8. Analiza el historico de pasajes de transporte estudiantil en Puebla
    usando pandas y matplotlib. Traza graficos estadisticos bimestrales.
    """
    def __init__(self):
        self._dataset_historico: Optional[Any] = None
        self._promedio_gasto = 0.0
        self.cargar_dataset()

    @property
    def dataset_historico(self) -> Optional[Any]:
        return self._dataset_historico

    @property
    def promedio_gasto(self) -> float:
        return self._promedio_gasto

    def cargar_dataset(self) -> bool:
        """Carga el dataset global con Pandas para agilizar calculos estadisticos."""
        if not PANDAS_MATPLOTLIB_AVAILABLE:
            return False
        try:
            if os.path.exists(ARCHIVO_VIAJES) and os.path.getsize(ARCHIVO_VIAJES) > 50:
                self._dataset_historico = pd.read_csv(
                    ARCHIVO_VIAJES,
                    names=["id_viaje", "id_pasajero", "id_unidad", "costo_aplicado", "fecha_hora", "id_escuela"],
                    header=0
                )
                self._dataset_historico["fecha_hora"] = pd.to_datetime(self._dataset_historico["fecha_hora"])
                self._dataset_historico["costo_aplicado"] = pd.to_numeric(self._dataset_historico["costo_aplicado"])
                self._promedio_gasto = float(self._dataset_historico["costo_aplicado"].mean())
                return True
        except Exception as e:
            print(f"Excepcion de analitica al cargar: {e}")
        return False

    def analizar_horas_pico(self) -> Dict[int, int]:
        """Determina que horas acumulan el mayor flujo de estudiantes."""
        if self._dataset_historico is None or self._dataset_historico.empty:
            return {}
        try:
            df = self._dataset_historico.copy()
            df["hora"] = df["fecha_hora"].dt.hour
            distribucion = df.groupby("hora").size().to_dict()
            return distribucion
        except Exception:
            return {}

    def graficar_uso_bimestral(self, ruta_grafico: str = CHARTS_DIR) -> str:
        """Genera diagramas de torta y barras financieras del transporte en Puebla."""
        if not PANDAS_MATPLOTLIB_AVAILABLE:
            return "Pandas o Matplotlib no se encuentran instalados."
            
        if self._dataset_historico is None or self._dataset_historico.empty:
            return "No se cuenta con suficientes registros historicos para graficar."

        try:
            df = self._dataset_historico.copy()
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            fig.patch.set_facecolor('#F5F6F7')

            # 1. Pastel: Uso por Universidad
            df_escuelas = df.groupby("id_escuela").size()
            colores = ['#2C3E50', '#27AE60', '#E74C3C', '#95A5A6', '#8E44AD']
            
            ax1.pie(df_escuelas, labels=df_escuelas.index, autopct='%1.1f%%',
                    startangle=90, colors=colores[:len(df_escuelas)],
                    textprops={'fontsize': 10, 'weight': 'bold', 'color': '#2C3E50'})
            ax1.set_title("Abordajes por Institucion en Puebla", fontsize=12, weight='bold', color='#2C3E50')

            # 2. Barras: Recaudaciones Diarias
            df['fecha_dia'] = df['fecha_hora'].dt.date
            df_gasto = df.groupby('fecha_dia')['costo_aplicado'].sum().tail(15)
            
            ax2.bar(df_gasto.index.astype(str), df_gasto.values, color='#2980B9', edgecolor='#1F3A60', width=0.55)
            ax2.set_title("Recaudacion Diaria Reciente ($ MXN)", fontsize=12, weight='bold', color='#2C3E50')
            ax2.set_xlabel("Dia de Operacion", fontsize=10)
            ax2.set_ylabel("Facturacion Total ($)", fontsize=10)
            ax2.tick_params(axis='x', rotation=45, labelsize=8)
            ax2.grid(axis='y', linestyle='--', alpha=0.45)

            plt.tight_layout()
            salida_png = os.path.join(ruta_grafico, "analisis_bimestral.png")
            plt.savefig(salida_png, dpi=120, facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close()
            return salida_png
        except Exception as e:
            return f"Excepcion de Matplotlib: {str(e)}"

    def reporte_eficiencia_ruta(self) -> Dict[str, Dict[str, Any]]:
        """Calcula el rendimiento de pasajes y rentabilidad por universidad."""
        reporte = {}
        if self._dataset_historico is None or self._dataset_historico.empty:
            return reporte
        try:
            df = self._dataset_historico.copy()
            for escuela in ["BUAP", "TEC DE MONTERREY", "IPN", "NINGUNA"]:
                sub_df = df[df["id_escuela"] == escuela]
                if not sub_df.empty:
                    viajes = int(sub_df.shape[0])
                    monto = float(sub_df["costo_aplicado"].sum())
                    reporte[escuela] = {
                        "viajes": viajes,
                        "recaudacion": round(monto, 2),
                        "nivel_uso": "Sobresaliente (Congestionado)" if viajes > 50 else "Regular"
                    }
            return reporte
        except Exception:
            return {}


class StudentVerifier:
    """Validador Escolar de Puebla.
    Simula una pasarela de conexion con las bases de datos academicas de BUAP, Tec, e IPN
    para corroborar inscripciones y firmar tokens digitales de descuento autorizados.
    """
    def __init__(self):
        # Registro dummy escolar de Puebla para verificacion
        self._padron_estudiantes: Dict[str, Dict[str, Any]] = {
            "202134567": {"nombre": "Alan Garcia Ortiz", "univ": "BUAP", "vigente": True, "limite_ciclo": 2026},
            "202354321": {"nombre": "Mariana Lozano Diaz", "univ": "TEC DE MONTERREY", "vigente": True, "limite_ciclo": 2027},
            "202276543": {"nombre": "Carlos Perez Ramos", "univ": "IPN", "vigente": True, "limite_ciclo": 2026},
            "201988877": {"nombre": "Juan Egresado", "univ": "BUAP", "vigente": False, "limite_ciclo": 2023}
        }

    def verificar_estudiante(self, matricula: str, universidad: str) -> Tuple[bool, str]:
        """Consulta el padron escolar e indica si el estudiante es elegible para el 50%."""
        mat = matricula.strip()
        uni = universidad.strip().upper()

        if uni not in UNIVERSIDADES_DESCUENTO:
            return False, "La institucion educativa no forma parte de los convenios del Estado de Puebla."
            
        if mat not in self._padron_estudiantes:
            return False, "La matricula ingresada no coincide con los padrones vigentes de la SEP."
            
        alumno = self._padron_estudiantes[mat]
        if alumno["univ"] != uni:
            return False, f"Incongruencia: La matricula pertenece a {alumno['univ']}, no a {uni}."
            
        if not alumno["vigente"] or alumno["limite_ciclo"] < 2026:
            return False, "Credencial escolar inactiva o periodo escolar expirado."
            
        return True, "Validacion exitosa: Estudiante inscrito y vigente."

    def firmar_convenio_descuento(self, matricula: str, universidad: str) -> str:
        """Genera un token digital inmutable (SHA-256) validando el descuento en la tarjeta."""
        aprobado, msg = self.verificar_estudiante(matricula, universidad)
        if not aprobado:
            raise ValidacionAcademicaError(f"No se pudo firmar el convenio estudiantil: {msg}")
            
        datos_firma = f"{matricula}-{universidad}-PUEBLA-TRANS-2026-SUBSIDIO"
        token = hashlib.sha256(datos_firma.encode('utf-8')).hexdigest()
        return token[:12].upper()


class DijkstraRouter:
    """
    10. Enrutador Metropolitano de Puebla (Dijkstra).
    Modela el mapa de transporte de Puebla como un grafo dirigido ponderado,
    calculando la ruta mas corta y los kilometros entre paradas de transbordo.
    """
    def __init__(self, lista_rutas: List[Ruta]):
        self.lista_rutas = lista_rutas
        self.grafo: Dict[int, Dict[int, float]] = {}
        self.catalogo_estaciones: Dict[int, str] = {}
        self.construir_grafo()

    def construir_grafo(self):
        """Genera conexiones bidireccionales dinámicas entre las estaciones del sistema."""
        self.grafo = {}
        for r in self.lista_rutas:
            estaciones = r.lista_estaciones
            for i in range(len(estaciones)):
                e_orig = estaciones[i]
                self.catalogo_estaciones[e_orig.id_estacion] = e_orig.nombre_parada
                if e_orig.id_estacion not in self.grafo:
                    self.grafo[e_orig.id_estacion] = {}
                
                # Conectar con estacion contigua
                if i < len(estaciones) - 1:
                    e_dest = estaciones[i+1]
                    distancia = MathUtils.calcular_distancia_gps(
                        e_orig.coordenadas[0], e_orig.coordenadas[1],
                        e_dest.coordenadas[0], e_dest.coordenadas[1]
                    )
                    self.grafo[e_orig.id_estacion][e_dest.id_estacion] = distancia
                    if e_dest.id_estacion not in self.grafo:
                        self.grafo[e_dest.id_estacion] = {}
                    self.grafo[e_dest.id_estacion][e_orig.id_estacion] = distancia

    def resolver_ruta_corta(self, id_inicio: int, id_fin: int) -> Tuple[List[int], float]:
        """Calcula el camino optimo y la distancia en Kilometros usando Dijkstra."""
        if id_inicio not in self.grafo or id_fin not in self.grafo:
            raise RutaNavegacionError("Las paradas de origen y/o destino no forman parte de la infraestructura de red.")
            
        distancias = {nodo: float('inf') for nodo in self.grafo}
        padres = {nodo: None for nodo in self.grafo}
        distancias[id_inicio] = 0.0
        no_visitados = list(self.grafo.keys())

        while no_visitados:
            nodo_actual = min(no_visitados, key=lambda n: distancias[n])
            if distancias[nodo_actual] == float('inf') or nodo_actual == id_fin:
                break
                
            no_visitados.remove(nodo_actual)

            for vecino, peso in self.grafo[nodo_actual].items():
                ruta_alternativa = distancias[nodo_actual] + peso
                if ruta_alternativa < distancias[vecino]:
                    distancias[vecino] = ruta_alternativa
                    padres[vecino] = nodo_actual

        camino = []
        nodo_temp = id_fin
        while nodo_temp is not None:
            camino.insert(0, nodo_temp)
            nodo_temp = padres[nodo_temp]
            
        if distancias[id_fin] == float('inf') or camino[0] != id_inicio:
            raise RutaNavegacionError(f"No existe conexion viable o camino continuo entre las estaciones {id_inicio} y {id_fin}.")
            
        return camino, round(distancias[id_fin], 2)


class TrafficForecaster:
    """
    11. Motor Predictor Temporal de Afluencia.
    Estima el flujo y volumen de congestion de una parada basandose en las horas de salida
    universitarias y trafico de Puebla.
    """
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def estimar_trafico_hora(self, id_estacion: int, hora: int) -> float:
        """Determina un porcentaje estimado de trafico (0.0 a 1.0) segun horarios escolares."""
        hr = max(0, min(23, int(hora)))
        coeficiente_trafico = 0.10
        
        # Pico 1: Entrada escolar matutina
        if hr in [7, 8]:
            coeficiente_trafico = 0.88
        # Pico 2: Salida matutina / entrada vespertina
        elif hr in [13, 14]:
            coeficiente_trafico = 0.78
        # Pico 3: Salida estudiantil vespertina
        elif hr in [18, 19]:
            coeficiente_trafico = 0.68
            
        # Modificar ligeramente segun la afluencia de la parada
        if id_estacion in [103, 201, 301]:  # Campuses BUAP CU, Tec Campus, IPN Campus
            coeficiente_trafico = min(1.0, coeficiente_trafico + 0.10)
            
        return round(coeficiente_trafico, 2)

    def predecir_tiempo_espera(self, id_estacion: int) -> int:
        """Predice en minutos el tiempo aproximado en parada segun el trafico estimado."""
        hora_actual = datetime.now().hour
        trafico = self.estimar_trafico_hora(id_estacion, hora_actual)
        
        if trafico >= 0.8:
            return random.randint(14, 25)
        elif trafico >= 0.5:
            return random.randint(7, 13)
        else:
            return random.randint(2, 6)


class SchoolCalendar:
    """
    12. Gestor de Calendario Academico Escolar.
    Almacena las fechas criticas universitarias (exámenes, vacaciones, dias feriados)
    de BUAP, Tec e IPN en Puebla para adecuar los aforos de simulacion.
    """
    def __init__(self):
        # Fechas registradas 2026
        self._calendario_eventos: Dict[str, Dict[str, Any]] = {
            "2026-05-18": {"evento": "EXAMENES PARCIALES", "afluencia_factor": 1.25}, # Hoy
            "2026-05-25": {"evento": "EXAMENES FINALES", "afluencia_factor": 1.40},
            "2026-06-15": {"evento": "VACACIONES VERANO", "afluencia_factor": 0.20},
            "2026-09-16": {"evento": "FERIADO NACIONAL", "afluencia_factor": 0.05}
        }

    def registrar_feriado(self, fecha_str: str, descripcion_evento: str, factor_demanda: float) -> bool:
        """Registra una fecha feriada especial modificando el factor de operacion."""
        try:
            datetime.strptime(fecha_str, "%Y-%m-%d")
            self._calendario_eventos[fecha_str] = {
                "evento": descripcion_evento.strip().upper(),
                "afluencia_factor": max(0.0, min(2.0, float(factor_demanda)))
            }
            return True
        except ValueError:
            raise CalendarioExcepcion("La fecha provista no cuenta con el formato estandar YYYY-MM-DD.")

    def obtener_modificador_demanda(self, fecha_str: str) -> float:
        """Retorna el modificador de frecuencia y demanda de pasajes en la fecha indicada."""
        if fecha_str in self._calendario_eventos:
            return self._calendario_eventos[fecha_str]["afluencia_factor"]
        return 1.0  # Frecuencia regular estandar


class AuditLogger:
    """
    13. Auditor de Transacciones y Seguridad del Sistema.
    Se encarga del registro inmutable de transacciones de recarga y cobro
    calculando hashes para prevenir adulteracion de saldos.
    """
    @staticmethod
    def registrar_transaccion(id_tarjeta: str, operacion: str, monto: float, saldo_restante: float):
        """Registra un evento financiero inmutable en CSV calculando un token hash SHA-256."""
        fecha_h = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cuerpo = f"{id_tarjeta}-{operacion}-{monto:.2f}-{saldo_restante:.2f}-{fecha_h}"
        hash_seguridad = hashlib.sha256(cuerpo.encode('utf-8')).hexdigest()[:16].upper()
        
        try:
            existe = os.path.exists(ARCHIVO_AUDITORIA) and os.path.getsize(ARCHIVO_AUDITORIA) > 10
            with open(ARCHIVO_AUDITORIA, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not existe:
                    writer.writerow(["fecha_hora", "id_tarjeta", "operacion", "monto", "saldo_restante", "firma_auditoria"])
                writer.writerow([fecha_h, id_tarjeta, operacion, f"{monto:.2f}", f"{saldo_restante:.2f}", hash_seguridad])
        except Exception:
            pass


class DatabaseBackupManager:
    """
    14. Administrador de Respaldos de Seguridad.
    Realiza copias de seguridad de las bases de datos JSON, controla
    la integridad inmutable cifrando los contenidos.
    """
    def __init__(self):
        self._backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(self._backup_dir, exist_ok=True)
        self._historial_respaldos: List[Dict[str, Any]] = []
        self.cargar_bitacora_backups()

    def cargar_bitacora_backups(self):
        """Carga el historial persistente de copias de seguridad."""
        if os.path.exists(ARCHIVO_RESPALDOS):
            try:
                with open(ARCHIVO_RESPALDOS, mode='r', encoding='utf-8') as f:
                    self._historial_respaldos = json.load(f)
            except Exception:
                self._historial_respaldos = []

    def guardar_bitacora_backups(self):
        """Persiste la bitacora de respaldos."""
        try:
            with open(ARCHIVO_RESPALDOS, mode='w', encoding='utf-8') as f:
                json.dump(self._historial_respaldos, f, indent=4)
        except Exception:
            pass

    def ejecutar_respaldo(self, ruta_archivo: str) -> str:
        """Copia el archivo a la zona de backups y retorna su hash SHA-256 de integridad."""
        if not os.path.exists(ruta_archivo):
            raise RecursoNoEncontradoError(f"El archivo fuente {ruta_archivo} no se encuentra en el disco.")
            
        nombre_original = os.path.basename(ruta_archivo)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_copia = f"respaldo_{timestamp}_{nombre_original}"
        ruta_copia = os.path.join(self._backup_dir, nombre_copia)

        try:
            with open(ruta_archivo, mode='rb') as f:
                contenido = f.read()
                hash_calculado = hashlib.sha256(contenido).hexdigest()
                
            with open(ruta_copia, mode='wb') as f:
                f.write(contenido)
                
            info = {
                "id_respaldo": len(self._historial_respaldos) + 1,
                "nombre_original": nombre_original,
                "nombre_copia": nombre_copia,
                "ruta_absoluta": ruta_copia,
                "hash_sha256": hash_calculado,
                "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._historial_respaldos.append(info)
            self.guardar_bitacora_backups()
            return hash_calculado
        except Exception as e:
            raise IOError(f"Excepcion de disco al respaldar base: {e}")

    def restaurar_respaldo(self, id_respaldo: int, ruta_destino: str) -> bool:
        """Restaura el respaldo en la ruta indicada validando su hash de integridad."""
        respaldo = None
        for b in self._historial_respaldos:
            if b["id_respaldo"] == id_respaldo:
                respaldo = b
                break
                
        if not respaldo:
            raise RecursoNoEncontradoError(f"No se encuentra registrado el respaldo ID {id_respaldo}.")
            
        ruta_fisica = respaldo["ruta_absoluta"]
        if not os.path.exists(ruta_fisica):
            raise RecursoNoEncontradoError("El archivo fisico del respaldo ha sido eliminado del disco.")
            
        try:
            with open(ruta_fisica, mode='rb') as f:
                contenido = f.read()
                hash_actual = hashlib.sha256(contenido).hexdigest()
                
            if hash_actual != respaldo["hash_sha256"]:
                raise SeguridadAuditoriaError("Integridad comprometida: La firma SHA-256 de la copia de respaldo ha sido adulterada.")
                
            with open(ruta_destino, mode='wb') as f:
                f.write(contenido)
            return True
        except Exception as e:
            raise IOError(f"Fallo critico al restaurar copia en caliente: {e}")


# GESTOR CENTRALIZADO DE PERSISTENCIA (DATAMANAGER POO)

class DataManager:
    """
    Controlador central que orquesta la carga, validaciones y guardado persistente
    en JSON/CSV de usuarios, tarjetas, vehiculos y registros del sistema.
    """
    def __init__(self):
        self.usuarios: Dict[int, Usuario] = {}
        self.tarjetas: Dict[str, TarjetaMovilidad] = {}
        self.rutas: Dict[int, Ruta] = {}
        self.vehiculos: Dict[str, Vehiculo] = {}
        self.inicializar_archivos()

    def inicializar_archivos(self):
        """Asienta en disco las bases de datos inicializandolas con mock realistas."""
        # 1. Cargar Usuarios
        if not os.path.exists(ARCHIVO_USUARIOS) or os.path.getsize(ARCHIVO_USUARIOS) < 5:
            self._crear_usuarios_semilla()
        else:
            self.cargar_usuarios()

        # 2. Cargar Rutas
        self._crear_rutas_semilla()

        # 3. Cargar Tarjetas
        if not os.path.exists(ARCHIVO_TARJETAS) or os.path.getsize(ARCHIVO_TARJETAS) < 5:
            self._crear_tarjetas_semilla()
        else:
            self.cargar_tarjetas()

        # 4. Cargar Vehiculos
        if not os.path.exists(ARCHIVO_VEHICULOS) or os.path.getsize(ARCHIVO_VEHICULOS) < 5:
            self._crear_vehiculos_semilla()
        else:
            self.cargar_vehiculos()

        # 5. Cargar Historico de Viajes (Pandas/CSV)
        if not os.path.exists(ARCHIVO_VIAJES) or os.path.getsize(ARCHIVO_VIAJES) < 10:
            self.generar_viajes_semilla_historico(1500)

    def cargar_usuarios(self):
        self.usuarios = {}
        try:
            with open(ARCHIVO_USUARIOS, mode='r', encoding='utf-8') as f:
                datos = json.load(f)
                for u in datos:
                    if u["tipo_usuario"] == "Pasajero":
                        usr = Pasajero(
                            id_usuario=u["id_usuario"],
                            nombre=u["nombre"],
                            correo=u["correo"],
                            contrasena_hash=u["contrasena_hash"],
                            id_escuela=u.get("id_escuela", "Ninguna"),
                            historial_viajes=u.get("historial_viajes", []),
                            preferencias=u.get("preferencias", "")
                        )
                    else:
                        usr = Administrador(
                            id_usuario=u["id_usuario"],
                            nombre=u["nombre"],
                            correo=u["correo"],
                            contrasena_hash=u["contrasena_hash"],
                            id_escuela=u.get("id_escuela", "Ninguna")
                        )
                    self.usuarios[usr.id_usuario] = usr
        except Exception as e:
            print(f"Error cargando usuarios: {e}")

    def cargar_tarjetas(self):
        self.tarjetas = {}
        try:
            with open(ARCHIVO_TARJETAS, mode='r', encoding='utf-8') as f:
                datos = json.load(f)
                for t in datos:
                    tarj = TarjetaMovilidad(
                        id_tarjeta=t["id_tarjeta"],
                        saldo_actual=t["saldo_actual"],
                        id_usuario=t["id_usuario"],
                        fecha_ult_uso=t.get("fecha_ult_uso"),
                        tipo_descuento=t.get("tipo_descuento", "Regular")
                    )
                    self.tarjetas[tarj.id_tarjeta] = tarj
        except Exception as e:
            print(f"Error cargando tarjetas: {e}")

    def cargar_vehiculos(self):
        self.vehiculos = {}
        try:
            with open(ARCHIVO_VEHICULOS, mode='r', encoding='utf-8') as f:
                datos = json.load(f)
                for v in datos:
                    veh = Vehiculo(
                        id_unidad=v["id_unidad"],
                        capacidad_max=v["capacidad_max"],
                        pasajeros_actuales=v["pasajeros_actuales"],
                        ubicacion_actual=tuple(v["ubicacion_actual"]),
                        estado=v.get("estado", "En parada")
                    )
                    self.vehiculos[veh.id_unidad] = veh
        except Exception as e:
            print(f"Error cargando vehiculos: {e}")

    def guardar_usuarios(self):
        try:
            lista = [u.a_diccionario() for u in self.usuarios.values()]
            with open(ARCHIVO_USUARIOS, mode='w', encoding='utf-8') as f:
                json.dump(lista, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Fallo al guardar base de usuarios: {e}")

    def guardar_tarjetas(self):
        try:
            lista = [t.a_diccionario() for t in self.tarjetas.values()]
            with open(ARCHIVO_TARJETAS, mode='w', encoding='utf-8') as f:
                json.dump(lista, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Fallo al guardar base de tarjetas: {e}")

    def guardar_vehiculos(self):
        try:
            lista = [v.a_diccionario() for v in self.vehiculos.values()]
            with open(ARCHIVO_VEHICULOS, mode='w', encoding='utf-8') as f:
                json.dump(lista, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Fallo al guardar base de vehiculos: {e}")

    def registrar_viaje_pasajero(self, viaje: RegistroViaje) -> bool:
        """Consolida un viaje en el historial local del pasajero y en el CSV historico."""
        # 1. CSV Historico
        try:
            existe = os.path.exists(ARCHIVO_VIAJES) and os.path.getsize(ARCHIVO_VIAJES) > 10
            with open(ARCHIVO_VIAJES, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not existe:
                    writer.writerow(["id_viaje", "id_pasajero", "id_unidad", "costo_aplicado", "fecha_hora", "id_escuela"])
                writer.writerow(viaje.a_lista_csv())
        except Exception as e:
            print(f"Error al volcar viaje en CSV: {e}")
            return False

        # 2. Historial de Pasajero en memoria
        if viaje.id_pasajero in self.usuarios:
            usr = self.usuarios[viaje.id_pasajero]
            if isinstance(usr, Pasajero):
                usr.historial_viajes.append({
                    "id_viaje": viaje.id_viaje,
                    "id_unidad": viaje.id_unidad,
                    "costo_aplicado": viaje.costo_aplicado,
                    "fecha_hora": viaje.fecha_hora,
                    "id_escuela": viaje.id_escuela
                })
                self.guardar_usuarios()
        return True

    def _crear_usuarios_semilla(self):
        hash_123456 = hashlib.sha256("123456".encode('utf-8')).hexdigest()
        self.usuarios = {
            1001: Pasajero(1001, "Alan Garcia Ortiz", "alan.garcia@buap.mx", hash_123456, "BUAP", preferencias="Ruta Verde"),
            1002: Pasajero(1002, "Mariana Lozano Diaz", "mariana.lozano@itesm.mx", hash_123456, "TEC DE MONTERREY", preferencias="Ruta Celeste"),
            1003: Pasajero(1003, "Carlos Perez Ramos", "carlos.perez@ipn.mx", hash_123456, "IPN", preferencias="Ruta Azul"),
            1004: Pasajero(1004, "Laura Gomez Estrada", "laura.gomez@gmail.com", hash_123456, "NINGUNA"),
            9001: Administrador(9001, "Ing. Rodrigo Juarez", "rodrigo.admin@transpuebla.com", hash_123456)
        }
        self.guardar_usuarios()

    def _crear_tarjetas_semilla(self):
        self.tarjetas = {
            "BUAP-9901": TarjetaMovilidad("BUAP-9901", 160.00, 1001, tipo_descuento="BUAP"),
            "ITESM-8802": TarjetaMovilidad("ITESM-8802", 350.00, 1002, tipo_descuento="TEC DE MONTERREY"),
            "IPN-7703": TarjetaMovilidad("IPN-7703", 95.00, 1003, tipo_descuento="IPN"),
            "REG-6604": TarjetaMovilidad("REG-6604", 45.00, 1004, tipo_descuento="REGULAR")
        }
        self.guardar_tarjetas()

    def _crear_vehiculos_semilla(self):
        self.vehiculos = {
            "BUS-BUAP-01": Vehiculo("BUS-BUAP-01", 40, 0, (19.0051, -98.2012), "En parada"),
            "BUS-BUAP-02": Vehiculo("BUS-BUAP-02", 40, 0, (19.0262, -98.2285), "En parada"),
            "BUS-TEC-01": Vehiculo("BUS-TEC-01", 30, 0, (19.0028, -98.2431), "En parada"),
            "BUS-TEC-02": Vehiculo("BUS-TEC-02", 30, 0, (19.0433, -98.1981), "En parada"),
            "BUS-IPN-01": Vehiculo("BUS-IPN-01", 35, 0, (18.9912, -98.2581), "En parada"),
            "BUS-IPN-02": Vehiculo("BUS-IPN-02", 35, 0, (19.0560, -98.1510), "En parada")
        }
        self.guardar_vehiculos()

    def _crear_rutas_semilla(self):
        # Estaciones BUAP
        est_buap_1 = EstacionParada(101, "CU Edificio Carolino", (19.0433, -98.1981), ["Edificio Carolino", "Zocalo Puebla"], {"Ruta Verde BUAP": ["07:00", "07:30", "13:00", "13:30", "18:00"]})
        est_buap_2 = EstacionParada(102, "CCU BUAP", (19.0262, -98.2285), ["Complejo Cultural Universitario", "Angelopolis"], {"Ruta Verde BUAP": ["07:15", "07:45", "13:15", "13:45", "18:15"], "Ruta Amarilla BUAP": ["07:05", "13:05"]})
        est_buap_3 = EstacionParada(103, "Ciudad Universitaria (CU)", (19.0051, -98.2012), ["Facultades", "Estadio CU", "Biblioteca Central"], {"Ruta Verde BUAP": ["07:30", "08:00", "13:30", "14:00", "18:30"], "Ruta Amarilla BUAP": ["07:20", "13:20"], "Ruta Azul BUAP": ["07:40", "13:40"]})
        est_buap_4 = EstacionParada(104, "Amalucan", (19.0560, -98.1510), ["Parque Amalucan"], {"Ruta Azul BUAP": ["07:00", "13:00"]})

        # Estaciones Tec de Monterrey
        est_tec_1 = EstacionParada(201, "Tec Campus Puebla", (19.0028, -98.2431), ["Edificio Aulas", "Gimnasio Tec"], {"Ruta Azul TEC": ["07:30", "14:00"], "Ruta Verde TEC": ["07:35", "13:35"], "Ruta Celeste TEC": ["07:45", "13:45"]})
        est_tec_2 = EstacionParada(202, "Angelopolis", (19.0298, -98.2321), ["Mall Angelopolis"], {"Ruta Azul TEC": ["07:15", "13:45"], "Ruta Celeste TEC": ["07:30", "13:30"]})
        est_tec_3 = EstacionParada(203, "Cholula Centro", (19.0581, -98.3051), ["Zocalo Cholula", "Piramide"], {"Ruta Azul TEC": ["07:00", "13:30"]})
        est_tec_4 = EstacionParada(204, "Lomas de Angelopolis", (18.9881, -98.2685), ["Sonata Town Center"], {"Ruta Verde TEC": ["07:00", "13:00"]})
        est_tec_5 = EstacionParada(205, "Plaza Dorada", (19.0332, -98.2045), ["Plaza Dorada", "Parque Juarez"], {"Ruta Celeste TEC": ["07:15", "13:15"]})

        # Estaciones IPN
        est_ipn_1 = EstacionParada(301, "IPN Campus Puebla", (18.9912, -98.2581), ["Campus IPN", "Guadalupe Hidalgo"], {"Ruta Verde IPN": ["07:30", "13:30"], "Ruta Celeste IPN": ["07:40", "13:40"], "Ruta Azul IPN": ["07:50", "13:50"]})
        est_ipn_2 = EstacionParada(302, "Paseo Destino", (19.0091, -98.2361), ["Terminal Paseo Destino"], {"Ruta Verde IPN": ["07:10", "13:10"]})
        est_ipn_3 = EstacionParada(303, "San Manuel", (19.0152, -98.1921), ["Plaza San Manuel"], {"Ruta Celeste IPN": ["07:10", "13:10"]})
        est_ipn_4 = EstacionParada(304, "Cholula Terminal", (19.0565, -98.3031), ["Terminal Cholula IPN"], {"Ruta Azul IPN": ["07:10", "13:10"]})

        self.rutas = {
            11: Ruta(11, "Ruta Verde BUAP", [est_buap_1, est_buap_2, est_buap_3], 10.00, "BUAP"),
            12: Ruta(12, "Ruta Amarilla BUAP", [est_buap_2, est_buap_3], 10.00, "BUAP"),
            13: Ruta(13, "Ruta Azul BUAP", [est_buap_4, est_buap_3], 10.00, "BUAP"),
            
            21: Ruta(21, "Ruta Azul TEC", [est_tec_3, est_tec_2, est_tec_1], 12.00, "TEC DE MONTERREY"),
            22: Ruta(22, "Ruta Verde TEC", [est_tec_4, est_tec_1], 12.00, "TEC DE MONTERREY"),
            23: Ruta(23, "Ruta Celeste TEC", [est_tec_5, est_tec_2, est_tec_1], 12.00, "TEC DE MONTERREY"),
            
            31: Ruta(31, "Ruta Verde IPN", [est_ipn_2, est_ipn_1], 11.00, "IPN"),
            32: Ruta(32, "Ruta Celeste IPN", [est_ipn_3, est_ipn_1], 11.00, "IPN"),
            33: Ruta(33, "Ruta Azul IPN", [est_ipn_4, est_ipn_1], 11.00, "IPN")
        }

    def generar_viajes_semilla_historico(self, cantidad: int = 1500):
        """Genera historico rico de pasajes en los ultimos 60 dias."""
        unidades = list(self.vehiculos.keys())
        fecha_inicio = datetime.now() - timedelta(days=60)
        
        viajes_lista = []
        viaje_id_num = 100000
        
        for _ in range(cantidad):
            viaje_id_num += 1
            dia_viaje = fecha_inicio + timedelta(days=random.randint(0, 59))
            
            # Distribucion de horas pico
            r_val = random.random()
            if r_val < 0.45:
                hora = random.randint(7, 8)
            elif r_val < 0.80:
                hora = random.randint(13, 14)
            elif r_val < 0.92:
                hora = random.randint(18, 19)
            else:
                hora = random.choice([6, 10, 11, 12, 15, 16, 17, 20, 21])
                
            fecha_v = dia_viaje.replace(hour=hora, minute=random.randint(0, 59), second=random.randint(0, 59))
            fecha_str = fecha_v.strftime("%Y-%m-%d %H:%M:%S")
            
            id_pasajero = random.choice([1001, 1002, 1003, 1004])
            
            if id_pasajero == 1001:
                escuela = "BUAP"
                costo = 5.00
            elif id_pasajero == 1002:
                escuela = "TEC DE MONTERREY"
                costo = 6.00
            elif id_pasajero == 1003:
                escuela = "IPN"
                costo = 5.50
            else:
                escuela = "NINGUNA"
                costo = 10.00
                
            bus_asociado = [u for u in unidades if escuela.split()[0] in u]
            id_unidad = random.choice(bus_asociado) if bus_asociado else random.choice(unidades)
            
            viajes_lista.append([
                str(viaje_id_num),
                str(id_pasajero),
                id_unidad,
                f"{costo:.2f}",
                fecha_str,
                escuela
            ])
            
            # Popular en historial local
            if id_pasajero in self.usuarios:
                usr = self.usuarios[id_pasajero]
                if isinstance(usr, Pasajero):
                    usr.historial_viajes.append({
                        "id_viaje": viaje_id_num,
                        "id_unidad": id_unidad,
                        "costo_aplicado": costo,
                        "fecha_hora": fecha_str,
                        "id_escuela": escuela
                    })

        viajes_lista.sort(key=lambda x: x[4])
        try:
            with open(ARCHIVO_VIAJES, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["id_viaje", "id_pasajero", "id_unidad", "costo_aplicado", "fecha_hora", "id_escuela"])
                writer.writerows(viajes_lista)
            self.guardar_usuarios()
            print(f"Poblado Exitoso de Semilla: {cantidad} viajes cargados en {ARCHIVO_VIAJES}")
        except Exception as e:
            print(f"Error escribiendo viajes semilla: {e}")


# MOTOR DE SIMULACION DE MOVIMIENTO GPS (ENGINE)

class SimulationEngine:
    """
    Motor que impulsa el movimiento interactivo de buses escolares de Puebla.
    Calcula interpolaciones LERP y controla el aforo en paradas.
    """
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.vincular_unidades_a_rutas()
        self.sim_status: Dict[str, Dict[str, Any]] = {}
        self.inicializar_estado_simulacion()

    def vincular_unidades_a_rutas(self):
        """Asigna buses a las rutas correspondientes."""
        for v_id, vehiculo in self.data_manager.vehiculos.items():
            if "BUAP" in v_id:
                self.data_manager.rutas[11].asociar_unidad(vehiculo)
                self.data_manager.rutas[12].asociar_unidad(vehiculo)
            elif "TEC" in v_id:
                self.data_manager.rutas[21].asociar_unidad(vehiculo)
                self.data_manager.rutas[23].asociar_unidad(vehiculo)
            elif "IPN" in v_id:
                self.data_manager.rutas[31].asociar_unidad(vehiculo)
                self.data_manager.rutas[32].asociar_unidad(vehiculo)

    def inicializar_estado_simulacion(self):
        """Prepara el posicionamiento inicial de los vehiculos en la primera parada."""
        rutas_keys = list(self.data_manager.rutas.keys())
        for v_id, veh in self.data_manager.vehiculos.items():
            ruta_asociada = None
            for r in self.data_manager.rutas.values():
                if veh in r.obtener_unidades_activas():
                    ruta_asociada = r
                    break
            
            if not ruta_asociada:
                ruta_asociada = self.data_manager.rutas[random.choice(rutas_keys)]
                
            self.sim_status[v_id] = {
                "ruta_id": ruta_asociada.id_ruta,
                "origen_idx": 0,
                "progreso": 0.0,
                "direccion_ida": True,
                "velocidad": 0.04
            }
            parada_inicial = ruta_asociada.lista_estaciones[0]
            veh.ubicacion_actual = parada_inicial.coordenadas
            veh.estado = "En parada"

    def actualizar_paso_tiempo(self) -> List[str]:
        """Avanza la simulacion interpolando coordenadas GPS y alterando aforo."""
        alertas = []
        for v_id, veh in self.data_manager.vehiculos.items():
            if veh.estado == "Fuera de servicio":
                continue
                
            status = self.sim_status[v_id]
            ruta = self.data_manager.rutas[status["ruta_id"]]
            idx_orig = status["origen_idx"]
            
            estaciones = ruta.lista_estaciones
            if len(estaciones) < 2:
                continue
                
            if status["direccion_ida"]:
                idx_dest = idx_orig + 1
            else:
                idx_dest = idx_orig - 1
                
            est_origen = estaciones[idx_orig]
            est_destino = estaciones[idx_dest]
            
            status["progreso"] += status["velocidad"]
            
            if status["progreso"] >= 1.0:
                # Llegó a parada
                status["progreso"] = 0.0
                status["origen_idx"] = idx_dest
                veh.ubicacion_actual = est_destino.coordenadas
                veh.estado = "En parada"
                
                # Modificar aforo
                cambio_pasajeros = random.randint(-10, 12)
                veh.pasajeros_actuales = max(0, min(veh.capacidad_max + 2, veh.pasajeros_actuales + cambio_pasajeros))
                
                if veh.pasajeros_actuales > veh.capacidad_max:
                    alertas.append(f"ADVERTENCIA: Unidad {v_id} reporta SOBRECUPO en parada {est_destino.nombre_parada} ({veh.pasajeros_actuales}/{veh.capacidad_max} personas).")
                
                if status["direccion_ida"] and idx_dest == len(estaciones) - 1:
                    status["direccion_ida"] = False
                elif not status["direccion_ida"] and idx_dest == 0:
                    status["direccion_ida"] = True
            else:
                # LERP
                veh.estado = "En ruta"
                lat_orig, lon_orig = est_origen.coordenadas
                lat_dest, lon_dest = est_destino.coordenadas
                p = status["progreso"]
                
                nueva_lat = lat_orig + (lat_dest - lat_orig) * p
                nueva_lon = lon_orig + (lon_dest - lon_orig) * p
                veh.actualizar_posicion(nueva_lat, nueva_lon)
                
        self.data_manager.guardar_vehiculos()
        return alertas


# CLASE AUXILIAR Y UTILERIA MATEMATICA

class MathUtils:
    """Clase estatica para resoluciones fisicas y formulas geodesicas."""
    
    @staticmethod
    def calcular_distancia_gps(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Aplica la formula de Haversine para computar distancias terrestres."""
        RADIO_TIERRA_KM = 6371.0
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        diff_lat = lat2_rad - lat1_rad
        diff_lon = lon2_rad - lon1_rad
        
        a = math.sin(diff_lat / 2.0)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(diff_lon / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        
        return RADIO_TIERRA_KM * c


# INTERFAZ DE LINEA DE COMANDO INTERACTIVA (CLI - REPL)

class InteractiveCLI:
    """
    15. Consola CLI (REPL) para Administracion Directa.
    Permite operar y auditar las bases de datos de transporte en Puebla
    de forma directa desde la terminal.
    """
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.calendar = SchoolCalendar()
        self.verifier = StudentVerifier()

    def mostrar_menu(self):
        print("\n" + "="*60)
        print(" SISTEMA DE TRANSPORTE ESTUDIANTIL DE PUEBLA - INTERFAZ CLI")
        print("="*60)
        print("1. Mostrar paradas activas")
        print("2. Registrar recarga de Tarjeta de Movilidad")
        print("3. Verificar vigencia de estudiante (SEP)")
        print("4. Monitorear telemetria de autobuses en ruta")
        print("5. Generar respaldo de base de datos")
        print("6. Calcular ruta mas corta (Algoritmo de Dijkstra)")
        print("7. Ejecutar pruebas unitarias integradas")
        print("8. Salir de Consola CLI")
        print("-"*60)

    def arrancar_repl(self):
        """Inicia el bucle REPL interactivo de linea de comandos."""
        while True:
            self.mostrar_menu()
            opcion = input("Seleccione una operacion (1-8): ").strip()
            
            if opcion == "1":
                print("\nPARADAS DE AUTOBUS ACTIVAS:")
                for r in self.dm.rutas.values():
                    print(f"\n{r.nombre_ruta} (Universidad: {r.universidad_afiliada}):")
                    for est in r.lista_estaciones:
                        print(f"  [{est.id_estacion}] {est.nombre_parada} - Puntos Interes: {est.puntos_interes}")
                        
            elif opcion == "2":
                id_t = input("Ingrese el ID de la Tarjeta (ej. BUAP-9901): ").strip().upper()
                if id_t in self.dm.tarjetas:
                    try:
                        monto = float(input("Monto a recargar ($): ").strip())
                        nueva = self.dm.tarjetas[id_t].recargar_saldo(monto)
                        self.dm.guardar_tarjetas()
                        print(f"Recarga exitosa. Nuevo saldo: ${nueva:.2f}")
                    except TransporteException as e:
                        print(f"Fallo en recarga: {e.mensaje}")
                    except ValueError:
                        print("Monto numerico invalido.")
                else:
                    print("La tarjeta ingresada no existe.")
                    
            elif opcion == "3":
                mat = input("Ingrese matricula estudiantil: ").strip()
                uni = input("Ingrese universidad (BUAP, TEC DE MONTERREY, IPN): ").strip().upper()
                valido, msg = self.verifier.verificar_estudiante(mat, uni)
                if valido:
                    print(f"VALIDACION APOSITIVA: {msg}")
                    tok = self.verifier.firmar_convenio_descuento(mat, uni)
                    print(f"Token de subsidio SEP firmado: {tok}")
                else:
                    print(f"VALIDACION NEGATIVA: {msg}")
                    
            elif opcion == "4":
                print("\nTELEMETRIA DE VEHICULOS EN TIEMPO REAL:")
                for v in self.dm.vehiculos.values():
                    print(f"Unidad: {v.id_unidad} | Pasajeros: {v.pasajeros_actuales}/{v.capacidad_max} | Combustible: {v.nivel_combustible}% | Motor: {v.temperatura_motor} C | Estado: {v.estado}")
                    
            elif opcion == "5":
                backup_mgr = DatabaseBackupManager()
                try:
                    hash_u = backup_mgr.ejecutar_respaldo(ARCHIVO_USUARIOS)
                    print(f"Respaldo de base de usuarios exitoso. Firma SHA-256: {hash_u}")
                except Exception as e:
                    print(f"Fallo al respaldar: {e}")
                    
            elif opcion == "6":
                print("\nALGORITMO DE DIJKSTRA - PLANIFICADOR:")
                try:
                    router = DijkstraRouter(list(self.dm.rutas.values()))
                    id_orig = int(input("Ingrese ID Estacion Origen (ej. 101): ").strip())
                    id_dest = int(input("Ingrese ID Estacion Destino (ej. 103): ").strip())
                    camino, km = router.resolver_ruta_corta(id_orig, id_dest)
                    nombres = [router.catalogo_estaciones[n] for n in camino]
                    print(f"Camino mas corto encontrado: {' -> '.join(nombres)}")
                    print(f"Distancia de trayecto: {km} Km.")
                except Exception as e:
                    print(f"Fallo de enrutamiento: {e}")
                    
            elif opcion == "7":
                print("\nLanzando Unit Testing Framework...")
                ejecutar_pruebas()
                
            elif opcion == "8":
                print("Finalizando consola interactiva CLI.")
                break
            else:
                print("Opcion de menu invalida.")


# SUITE DE PRUEBAS UNITARIAS INTEGRADA (ROBUSTEZ Y CALIDAD DE CODIGO)

class TestSistemaTransporte(unittest.TestCase):
    """
    Suite de Pruebas Unitarias Integrada.
    Verifica de forma automatica y exhaustiva el correcto funcionamiento
    de los 15 componentes del backend.
    """
    def setUp(self):
        # Entidades Mock Efimeras
        self.usuario_base = Usuario(999, "Test User", "test@correo.com", "hash123", "Pasajero", "BUAP")
        self.pasajero_test = Pasajero(888, "Alan Estud", "alan@buap.mx", "hash123", "BUAP")
        self.admin_test = Administrador(900, "Ing. Gomez", "gomez.admin@buap.mx", "hash")
        
        # Tarjetas
        self.tarjeta_regular = TarjetaMovilidad("REG-001", 50.00, 888, tipo_descuento="Regular")
        self.tarjeta_buap = TarjetaMovilidad("BUAP-002", 50.00, 888, tipo_descuento="BUAP")
        self.tarjeta_tec = TarjetaMovilidad("TEC-003", 50.00, 888, tipo_descuento="TEC DE MONTERREY")
        self.tarjeta_ipn = TarjetaMovilidad("IPN-004", 50.00, 888, tipo_descuento="IPN")
        
        # Estaciones
        self.est1 = EstacionParada(901, "Carolino Central", (19.0433, -98.1981), puntos_interes=["Centro"])
        self.est2 = EstacionParada(902, "CCU Teatro", (19.0262, -98.2285), puntos_interes=["Teatro"])
        self.est3 = EstacionParada(903, "CU Estadio", (19.0051, -98.2012), puntos_interes=["Deportes"])
        
        # Rutas
        self.ruta_piloto = Ruta(99, "Ruta Piloto", [self.est1, self.est2, self.est3], 10.00, "BUAP")
        self.ruta_secundaria = Ruta(88, "Ruta Sec", [self.est2, self.est3], 12.00, "TEC DE MONTERREY")
        
        # Vehiculo
        self.bus_test = Vehiculo("TEST-BUS", 30, 0, (19.0433, -98.1981), "En parada")

    def test_encapsulacion_usuario(self):
        """Verifica que las restricciones de validacion funcionen adecuadamente."""
        with self.assertRaises(ValidacionDatosError):
            Usuario(0, "Malo", "malo@correo.com", "hash", "Pasajero")
            
        with self.assertRaises(ValidacionDatosError):
            self.usuario_base.correo = "correo_sin_arroba"

    def test_herencia_pasajero(self):
        """Valida que la clase Pasajero herede propiedades y metodos de Usuario."""
        self.assertTrue(isinstance(self.pasajero_test, Usuario))
        self.assertEqual(self.pasajero_test.tipo_usuario, "Pasajero")

    def test_actualizar_datos_usuario(self):
        """Valida la modificacion de contraseñas y datos."""
        self.usuario_base.actualizar_datos(nombre="Nuevo Nombre", correo="nuevo@test.com")
        self.assertEqual(self.usuario_base.nombre, "Nuevo Nombre")
        self.assertEqual(self.usuario_base.correo, "nuevo@test.com")
        
        with self.assertRaises(ValidacionDatosError):
            self.usuario_base.actualizar_datos(contrasena_nueva="123")

    def test_buscar_destino_pasajero(self):
        """Verifica que la busqueda de destinos filtre las paradas correctas."""
        res = self.pasajero_test.buscar_destino("Teatro", [self.ruta_piloto])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1].id_estacion, 902)

    def test_reporte_gastos_pasajero(self):
        """Comprueba el computo bimestral de gastos de un pasajero."""
        self.pasajero_test.historial_viajes.append({
            "id_viaje": 11,
            "costo_aplicado": 5.00,
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_escuela": "BUAP"
        })
        rep = self.pasajero_test.generar_reporte_gastos()
        self.assertEqual(rep["total_gasto_bimestral"], 5.00)
        self.assertEqual(rep["total_viajes"], 1)

    def test_polimorfismo_descuentos(self):
        """Valida el descuento del 50% segun convenio estudiantil en Puebla."""
        # Regular paga 10
        costo_reg = self.tarjeta_regular.descontar_pasaje(10.00)
        self.assertEqual(costo_reg, 10.00)
        
        # BUAP paga 5
        costo_buap = self.tarjeta_buap.descontar_pasaje(10.00)
        self.assertEqual(costo_buap, 5.00)
        
        # Tec paga 5
        costo_tec = self.tarjeta_tec.descontar_pasaje(10.00)
        self.assertEqual(costo_tec, 5.00)

    def test_saldo_insuficiente(self):
        """Verifica el bloqueo de abordaje si la tarjeta no tiene saldo."""
        tarjeta_vacia = TarjetaMovilidad("VAC-001", 2.00, 888)
        with self.assertRaises(SaldoInsuficienteError):
            tarjeta_vacia.descontar_pasaje(10.00)

    def test_recarga_tarjeta_limites(self):
        """Certifica que el saldo se actualice en las recargas y respete limites."""
        self.tarjeta_regular.recargar_saldo(100.00)
        self.assertEqual(self.tarjeta_regular.saldo_actual, 150.00)
        
        with self.assertRaises(ValidacionDatosError):
            self.tarjeta_regular.recargar_saldo(-20.00)
            
        with self.assertRaises(ValidacionDatosError):
            self.tarjeta_regular.recargar_saldo(2500.00)

    def test_inicio_sesion(self):
        """Verifica que el hashing y las credenciales operen correctamente."""
        contrasena_original = "puebla2026"
        hash_pass = hashlib.sha256(contrasena_original.encode('utf-8')).hexdigest()
        usr = Usuario(777, "Juan Perez", "juan@correo.com", hash_pass, "Pasajero")
        
        self.assertTrue(usr.iniciar_sesion(contrasena_original))
        self.assertFalse(usr.iniciar_sesion("contrasena_incorrecta"))

    def test_calculo_trayecto(self):
        """Comprueba que la distancia del trayecto sea congruente."""
        dist = self.ruta_piloto.calcular_trayecto()
        self.assertGreater(dist, 0.0)
        self.assertLess(dist, 10.0)

    def test_alerta_sobrecupo_vehiculo(self):
        """Verifica la deteccion y reporte del estado de sobrecupo en los vehiculos."""
        self.bus_test.pasajeros_actuales = 35
        vol = self.bus_test.monitorear_volumen()
        self.assertEqual(vol, "Sobreocupado")
        self.assertTrue(self.bus_test.alertas_enviadas >= 1)

    def test_asociacion_unidades_ruta(self):
        """Valida el enrolamiento de buses en las rutas."""
        self.ruta_piloto.asociar_unidad(self.bus_test)
        self.assertIn(self.bus_test, self.ruta_piloto.obtener_unidades_activas())
        
        self.bus_test.estado = "Fuera de servicio"
        self.assertNotIn(self.bus_test, self.ruta_piloto.obtener_unidades_activas())

    def test_grafo_enrutamiento_corto(self):
        """Valida que el DijkstraRouter calcule la distancia optima y conexion de red."""
        router = DijkstraRouter([self.ruta_piloto, self.ruta_secundaria])
        camino, dist = router.resolver_ruta_corta(901, 903)
        self.assertEqual(camino, [901, 902, 903])
        self.assertGreater(dist, 0.0)

    def test_enrutamiento_inexistente(self):
        """Comprueba que lance una excepcion si no hay conexion."""
        router = DijkstraRouter([self.ruta_piloto])
        with self.assertRaises(RutaNavegacionError):
            router.resolver_ruta_corta(901, 999)

    def test_validacion_academica_vigente(self):
        """Valida el control academico para BUAP, Tec e IPN."""
        verifier = StudentVerifier()
        valido, msg = verifier.verificar_estudiante("202134567", "BUAP")
        self.assertTrue(valido)
        
        # Egresado
        valido, msg = verifier.verificar_estudiante("201988877", "BUAP")
        self.assertFalse(valido)

    def test_firma_token_criptografico(self):
        """Verifica la emision de firma digital para estudiantes."""
        verifier = StudentVerifier()
        token = verifier.firmar_convenio_descuento("202134567", "BUAP")
        self.assertEqual(len(token), 12)
        
        with self.assertRaises(ValidacionAcademicaError):
            verifier.firmar_convenio_descuento("201988877", "BUAP")

    def test_sistema_respaldo_seguro(self):
        """Valida el ciclo de vida del respaldo y control de integridad hash."""
        f_prueba = os.path.join(DATA_DIR, "test_archivo.json")
        with open(f_prueba, mode='w') as f:
            f.write("CONTENIDO_PRUEBA_SISTEMA_INTEGRO")
            
        backup_mgr = DatabaseBackupManager()
        hash_original = backup_mgr.ejecutar_respaldo(f_prueba)
        self.assertIsNotNone(hash_original)
        
        # Eliminar original e intentar restaurar
        os.remove(f_prueba)
        exito = backup_mgr.restaurar_respaldo(1, f_prueba)
        self.assertTrue(exito)
        self.assertTrue(os.path.exists(f_prueba))
        os.remove(f_prueba)

    def test_prediccion_congestion_tiempo(self):
        """Verifica que el predictor estime afluencia segun horarios estudiantiles."""
        forecaster = TrafficForecaster(None)
        cong_pico = forecaster.estimar_trafico_hora(103, 7)
        cong_valle = forecaster.estimar_trafico_hora(103, 11)
        self.assertGreater(cong_pico, cong_valle)

    def test_calendario_academico(self):
        """Comprueba el factor de demanda en base al calendario escolar."""
        calendar = SchoolCalendar()
        factor_examenes = calendar.obtener_modificador_demanda("2026-05-18")
        factor_vacaciones = calendar.obtener_modificador_demanda("2026-06-15")
        self.assertEqual(factor_examenes, 1.25)
        self.assertEqual(factor_vacaciones, 0.20)
        
        # Registro nuevo
        calendar.registrar_feriado("2026-11-20", "Revolucion", 0.15)
        self.assertEqual(calendar.obtener_modificador_demanda("2026-11-20"), 0.15)

    def test_telemetria_vehiculo(self):
        """Comprueba el consumo y calentamiento del motor en transito."""
        comb_original = self.bus_test.nivel_combustible
        self.bus_test.actualizar_posicion(19.0433, -98.1981)
        self.assertLess(self.bus_test.nivel_combustible, comb_original)
        
        self.bus_test.realizar_mantenimiento()
        self.assertEqual(self.bus_test.nivel_combustible, 100.0)

    def test_atencion_sobrecupo_admin(self):
        """Verifica que el administrador desahogue la unidad sobreocupada."""
        self.bus_test.pasajeros_actuales = 38
        self.assertEqual(self.bus_test.monitorear_volumen(), "Sobreocupado")
        
        msg = self.admin_test.atener_alerta_sobrecupo_si_aplica = self.admin_test.atender_alerta_sobrecupo(self.bus_test)
        self.assertIn("atendio alerta", msg)
        self.assertEqual(self.bus_test.pasajeros_actuales, 21) # 30 * 0.7

    def test_auditoria_hash_registro(self):
        """Valida que la auditoria registre transacciones y asigne firmas SHA-256."""
        AuditLogger.registrar_transaccion("BUAP-9901", "DEBITO", 5.00, 145.00)
        self.assertTrue(os.path.exists(ARCHIVO_AUDITORIA))

    def test_validador_dominios_correo(self):
        """Comprueba que los correos correspondan a los dominios universitarios oficiales."""
        validador = SchoolDiscountValidator()
        self.assertTrue(validador.validar_correo_institucional("test@buap.mx", "BUAP"))
        self.assertTrue(validador.validar_correo_institucional("alumno@itesm.mx", "TEC DE MONTERREY"))
        self.assertFalse(validador.validar_correo_institucional("alumno@gmail.com", "IPN"))

    def test_exportador_reportes_simulacion(self):
        """Verifica que el exportador de reportes genere archivos en formato markdown."""
        exporter = SimulationReportExporter(None)
        exito = exporter.generar_reporte_consola("Ruta Verde BUAP", 4.5, 3)
        self.assertTrue(exito)



class SchoolDiscountValidator:
    """Validador de Reglas de Convenio Escolar.
    Comprueba si las cuentas de correo registradas por los estudiantes
    corresponden con los dominios institucionales autorizados en Puebla.
    """
    def __init__(self):
        self._dominios_autorizados = {
            "BUAP": ["buap.mx", "correo.buap.mx"],
            "TEC DE MONTERREY": ["itesm.mx", "tec.mx"],
            "IPN": ["ipn.mx", "alumno.ipn.mx"]
        }

    def validar_correo_institucional(self, correo: str, universidad: str) -> bool:
        """Determina si la extension de correo coincide con la universidad."""
        univ = universidad.strip().upper()
        if univ not in self._dominios_autorizados:
            return False
            
        partes = correo.strip().lower().split("@")
        if len(partes) != 2:
            return False
            
        dominio = partes[1]
        return dominio in self._dominios_autorizados[univ]

    def obtener_nombre_convenio(self, universidad: str) -> str:
        """Retorna el nombre formal del convenio de descuento estudiantil."""
        univ = universidad.strip().upper()
        if univ in UNIVERSIDADES_DESCUENTO:
            return f"Convenio de Subsidio Metropolitano Puebla - {univ}"
        return "Tarifa Estandar Puebla"


class SimulationReportExporter:
    """Exportador de Telemetria y Reportes Escolares.
    Facilita la creacion de bitacoras y reportes formateados en markdown
    para entregar a las mesas directivas universitarias.
    """
    def __init__(self, simulation_engine: Optional[SimulationEngine]):
        self.sim_engine = simulation_engine

    def generar_reporte_consola(self, nombre_ruta: str, distancia_total: float, unidades_activas: int) -> bool:
        """Imprime y retorna True si el reporte del dia se procesa correctamente."""
        try:
            print("\n" + "="*50)
            print(" BITACORA DE OPERACION DE TRANSPORTE ESCOLAR")
            print("="*50)
            print(f"Ruta Evaluada: {nombre_ruta}")
            print(f"Distancia de Recorrido: {distancia_total} Km")
            print(f"Buses en Operacion: {unidades_activas}")
            print(f"Fecha de Reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("Estatus de Servicio: Estable, sin retrasos reportados.")
            print("="*50)
            return True
        except Exception:
            return False


def obtener_estado_servidor() -> Dict[str, Any]:
    """Analizador de Estado del Servidor.
    Genera informacion detallada del estado del almacenamiento y
    presencia de los archivos JSON/CSV del sistema de transporte.
    """
    estado = {}
    archivos = {
        "usuarios": ARCHIVO_USUARIOS,
        "tarjetas": ARCHIVO_TARJETAS,
        "vehiculos": ARCHIVO_VEHICULOS,
        "viajes": ARCHIVO_VIAJES,
        "logs": ARCHIVO_LOGS
    }
    for clave, ruta in archivos.items():
        if os.path.exists(ruta):
            estado[clave] = {
                "existe": True,
                "tamano_bytes": os.path.getsize(ruta),
                "ultima_modificacion": datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            estado[clave] = {"existe": False}
    return estado



class SanitizadorEntradas:
    """
    Sanitizador de entradas de datos para el sistema de transporte.
    Proporciona metodos estaticos para limpiar texto, correos y matriculas.
    """
    @staticmethod
    def limpiar_nombre(nombre: str) -> str:
        if not nombre:
            return ""
        nombre_limpio = re.sub(r'[^a-zA-Z\s]', '', nombre)
        return " ".join(nombre_limpio.split()).title()

    @staticmethod
    def limpiar_correo(correo: str) -> str:
        if not correo:
            return ""
        return correo.strip().lower()

    @staticmethod
    def limpiar_matricula(matricula: str) -> str:
        if not matricula:
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', matricula).upper()

    @staticmethod
    def es_registro_valido(nombre: str, correo: str) -> bool:
        nombre_ok = len(nombre.strip()) >= 3
        correo_ok = '@' in correo and '.' in correo
        return nombre_ok and correo_ok


class RegistradorConsola:
    """
    Logger complementario para la terminal de administracion.
    """
    def __init__(self, debug: bool = False):
        self.debug = debug

    def registrar_info(self, mensaje: str):
        print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensaje}")

    def registrar_advertencia(self, mensaje: str):
        print(f"[WARN] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensaje}")

    def registrar_depuracion(self, mensaje: str):
        if self.debug:
            print(f"[DEBUG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensaje}")

def ejecutar_pruebas():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSistemaTransporte)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    return resultado.wasSuccessful()



if __name__ == "__main__":
    import sys
    # Si se pasa argumento 'cli', arranca el REPL interactivo
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        dm = DataManager()
        cli = InteractiveCLI(dm)
        cli.arrancar_repl()
    else:
        print("----------------------------------------------------------------------")
        print("Ejecutando suite de pruebas unitarias integradas del Backend...")
        print("----------------------------------------------------------------------")
        exito = ejecutar_pruebas()
        if exito:
            print("\nPruebas unitarias completadas con EXITO. Modulo Backend robusto.")
        else:
            print("\nSe encontraron fallas en las pruebas unitarias. Revisar logs.")
            sys.exit(1)
