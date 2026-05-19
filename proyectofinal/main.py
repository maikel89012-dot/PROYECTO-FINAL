# -*- coding: utf-8 -*-
"""
Modulo Frontend: Interfaz Grafica de Usuario (GUI) - Transporte Puebla 2026
-------------------------------------------------------------------------
Este modulo implementa el panel interactivo visual del sistema, permitiendo:
1. Onboarding y Registro: Logins con validacion de hash y registros de alumnos
   vinculando credenciales SEP BUAP, Tec, IPN y asignacion de subsidios del 50%.
2. Portal del Estudiante: Consulta de saldos, historico de gastos, y una pasarela
   simulada de recargas de Tarjetas de Movilidad.
3. Planificador de Viajes: Seleccion de paradas e integracion directa de Dijkstra
   para planificar trayectos inter-universidades.
4. Mapa de Transito Interactivo: Graficado en tiempo real de unidades en movimiento
   sobre los mapas customizados de cada universidad en un Canvas interactivo.
5. Consola Administrativa: Monitoreo de alertas de sobrecupo y renderizado directo
   de los graficos analiticos de Pandas y Matplotlib.

Diseno Estetico Premium:
- Paleta HSL en base a tonos Slate oscuro (#1A252F), Electric Blue (#2980B9),
  Accent Green (#27AE60) y Snow White (#ECF0F1).
- Fuentes tipograficas limpias y jerarquizadas.
- Micro-animaciones en botones, alertas flotantes, y actualizacion en hilos.
- Mínimo de 810 líneas de código reales, estructurado en clases de soporte GUI.
"""

import os
import sys
import hashlib
import random
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Importar el core de negocio del backend
try:
    from backend import (
        DataManager, SimulationEngine, DijkstraRouter, StudentVerifier,
        TrafficForecaster, RegistroViaje, SchoolDiscountValidator,
        EstadisticaSistema, TransporteException, ARCHIVO_USUARIOS, ARCHIVO_TARJETAS,
        Pasajero, TarjetaMovilidad, BASE_DIR, CHARTS_DIR
    )
except ImportError:
    messagebox.showerror("Error Critico", "No se pudo localizar el archivo backend.py en el directorio. Asegurese de que ambos modulos compartan la misma carpeta.")
    sys.exit(1)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_CANVAS_AVAILABLE = True
except ImportError:
    MATPLOTLIB_CANVAS_AVAILABLE = False

# CONFIGURACION DE COLORES Y ESTILOS DE LA GUI
COLOR_BG_PRINCIPAL = "#1A252F"   # Slate ultra oscuro
COLOR_CARD = "#2C3E50"           # Slate elegante
COLOR_TEXTO_BLANCO = "#ECF0F1"   # Blanco nieve
COLOR_TEXTO_MUTED = "#BDC3C7"    # Gris plata
COLOR_PRIMARIO = "#2980B9"       # Azul electrico
COLOR_PRIMARIO_HOVER = "#3498DB" # Azul claro
COLOR_ACCENTO_OK = "#27AE60"     # Verde exito
COLOR_ACCENTO_WARN = "#E74C3C"   # Rojo alerta
COLOR_ACCENTO_GOLD = "#F1C40F"   # Amarillo oro

# CLASE PRINCIPAL: APPLICACION GUI (FRAME CONTROLLER POO)

class TransporteApp(tk.Tk):
    """
    Controlador central de la GUI. Administra el tamano de ventana, inicializa
    el DataManager del backend, configura los estilos visuales de ttk,
    y gestiona la transicion e intercambio de vistas (frames) en caliente.
    """
    def __init__(self):
        super().__init__()
        self.title("Transporte Puebla 2026 - Control Escolar Metropolitano")
        self.geometry("1180x760")
        self.configure(bg=COLOR_BG_PRINCIPAL)
        self.resizable(True, True)

        # 1. Inicializar Motores del Backend
        self.data_manager = DataManager()
        self.sim_engine = SimulationEngine(self.data_manager)
        self.router = DijkstraRouter(list(self.data_manager.rutas.values()))
        self.student_verifier = StudentVerifier()
        self.discount_validator = SchoolDiscountValidator()
        self.traffic_forecaster = TrafficForecaster(self.data_manager)
        self.stats = EstadisticaSistema()

        # 2. Estado de Sesion del Usuario
        self.usuario_actual: Optional[Any] = None

        # 3. Aplicar Estilos TTK
        self.configurar_estilos_visuales()

        # 4. Contenedor Maestro para Intercambio de Pantallas
        self.contenedor = tk.Frame(self, bg=COLOR_BG_PRINCIPAL)
        self.contenedor.pack(side="top", fill="both", expand=True)
        self.contenedor.grid_rowconfigure(0, weight=1)
        self.contenedor.grid_columnconfigure(0, weight=1)

        # 5. Diccionario de Vistas
        self.frames: Dict[str, tk.Frame] = {}

        # Cargar las vistas iniciales
        self.inicializar_frames()
        self.mostrar_frame("Login")

        # 6. Lanzar actualizacion continua de simulacion en segundo plano (Tkinter After)
        self.bucle_simulacion()

    def configurar_estilos_visuales(self):
        """Ajusta las propiedades visuales y temas de los widgets ttk."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configurar colores de paneles
        self.style.configure(".", background=COLOR_BG_PRINCIPAL, foreground=COLOR_TEXTO_BLANCO)
        self.style.configure("TLabel", background=COLOR_BG_PRINCIPAL, foreground=COLOR_TEXTO_BLANCO, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=COLOR_PRIMARIO)
        self.style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground=COLOR_TEXTO_BLANCO)
        self.style.configure("Sub.TLabel", font=("Segoe UI", 11), foreground=COLOR_TEXTO_MUTED)

        # Tarjetas e Informacion (Frames con color alternativo)
        self.style.configure("Card.TFrame", background=COLOR_CARD, relief="flat")
        self.style.configure("Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXTO_BLANCO, font=("Segoe UI", 10))
        self.style.configure("CardTitle.TLabel", background=COLOR_CARD, foreground=COLOR_PRIMARIO, font=("Segoe UI", 12, "bold"))
        self.style.configure("CardStat.TLabel", background=COLOR_CARD, foreground=COLOR_ACCENTO_OK, font=("Segoe UI", 20, "bold"))

        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background=COLOR_PRIMARIO, foreground=COLOR_TEXTO_BLANCO, borderwidth=0, padding=8)
        self.style.map("TButton", background=[("active", COLOR_PRIMARIO_HOVER)])
        
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=COLOR_ACCENTO_OK, foreground=COLOR_TEXTO_BLANCO, borderwidth=0, padding=8)
        self.style.map("Accent.TButton", background=[("active", "#2ECC71")])

        self.style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background=COLOR_CARD, foreground=COLOR_TEXTO_BLANCO, borderwidth=0, padding=5)
        self.style.map("Action.TButton", background=[("active", COLOR_BG_PRINCIPAL)])

        # Campos de Entrada
        self.style.configure("TEntry", fieldbackground=COLOR_CARD, background=COLOR_CARD, foreground=COLOR_TEXTO_BLANCO, borderwidth=1)

        # Tablas (Treeview) Premium
        self.style.configure("Treeview", background=COLOR_CARD, foreground=COLOR_TEXTO_BLANCO, fieldbackground=COLOR_CARD, rowheight=26, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", background=COLOR_BG_PRINCIPAL, foreground=COLOR_TEXTO_BLANCO, font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", COLOR_PRIMARIO)])

    def inicializar_frames(self):
        """Inicializa e inyecta las pantallas en el contenedor maestro."""
        for F_Class, nombre in [(LoginFrame, "Login"), (RegistroFrame, "Registro"), 
                                (DashboardFrame, "Dashboard"), (LiveMapFrame, "Mapa"), 
                                (AdminFrame, "Admin")]:
            frame = F_Class(parent=self.contenedor, controller=self)
            self.frames[nombre] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def mostrar_frame(self, nombre: str):
        """Trae al frente la pantalla solicitada refrescando su contenido."""
        frame = self.frames[nombre]
        frame.tkraise()
        # Disparar actualizacion si el frame cuenta con cargador
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()

    def bucle_simulacion(self):
        """Hilo simulado interactivo que actualiza el movimiento de autobuses cada 2.5 segundos."""
        try:
            alertas = self.sim_engine.actualizar_paso_tiempo()
            # Si hay una alerta y el usuario logueado es Administrador, notificar
            if alertas and self.usuario_actual and self.usuario_actual.tipo_usuario == "Administrador":
                self.frames["Admin"].agregar_alerta(alertas[0])
            
            # Si el mapa interactivo se encuentra activo, redibujar buses
            map_frame = self.frames["Mapa"]
            if map_frame.winfo_viewable():
                map_frame.redibujar_elementos()

        except Exception as e:
            print(f"Error en bucle de simulacion: {e}")
            
        # Re-agendar el bucle
        self.after(2500, self.bucle_simulacion)


# PANTALLA 1: INICIO DE SESION (LOGIN)

class LoginFrame(tk.Frame):
    """Pantalla inicial de Onboarding que maneja autenticacion de pasajeros y administradores."""
    def __init__(self, parent: tk.Frame, controller: TransporteApp):
        super().__init__(parent, bg=COLOR_BG_PRINCIPAL)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Card de Acceso Central
        card = tk.Frame(self, bg=COLOR_CARD, bd=1, relief="flat", highlightbackground=COLOR_PRIMARIO, highlightthickness=1)
        card.grid(row=0, column=0, padx=20, pady=20, ipadx=40, ipady=40)
        card.grid_columnconfigure(0, weight=1)

        # Cargar logo de la app si esta disponible
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        self.img_logo_tk = None
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((120, 120), Image.Resampling.LANCZOS)
                self.img_logo_tk = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error cargando logo en GUI: {e}")

        # Elementos Visuales
        if self.img_logo_tk:
            lbl_logo = tk.Label(card, image=self.img_logo_tk, bg=COLOR_CARD)
            lbl_logo.grid(row=0, column=0, pady=(0, 15))
            row_start = 1
        else:
            row_start = 0

        lbl_titulo = ttk.Label(card, text="RUTA APP", style="Title.TLabel", background=COLOR_CARD)
        lbl_titulo.grid(row=row_start, column=0, pady=(0, 5))

        lbl_sub = ttk.Label(card, text="Red Escolar de Movilidad y Subsidios", style="Sub.TLabel", background=COLOR_CARD)
        lbl_sub.grid(row=row_start+1, column=0, pady=(0, 25))

        # Campos de Texto
        lbl_correo = ttk.Label(card, text="Direccion de Correo Electronico", style="Card.TLabel")
        lbl_correo.grid(row=row_start+2, column=0, sticky="w", pady=(0, 5))
        
        self.ent_correo = ttk.Entry(card, width=32, font=("Segoe UI", 11))
        self.ent_correo.grid(row=row_start+3, column=0, pady=(0, 15))
        self.ent_correo.insert(0, "alan.garcia@buap.mx")

        lbl_pass = ttk.Label(card, text="Contrasena de Acceso", style="Card.TLabel")
        lbl_pass.grid(row=row_start+4, column=0, sticky="w", pady=(0, 5))
        
        self.ent_pass = ttk.Entry(card, show="*", width=32, font=("Segoe UI", 11))
        self.ent_pass.grid(row=row_start+5, column=0, pady=(0, 25))
        self.ent_pass.insert(0, "123456")

        btn_entrar = ttk.Button(card, text="INICIAR SESION", command=self.procesar_login)
        btn_entrar.grid(row=row_start+6, column=0, sticky="ew", pady=(0, 10))

        # Registro Enlace
        lbl_nuevo = ttk.Label(card, text="¿Aun no cuentas con tarjeta de movilidad?", style="Sub.TLabel", background=COLOR_CARD, font=("Segoe UI", 9))
        lbl_nuevo.grid(row=row_start+7, column=0, pady=(15, 5))

        btn_registro = ttk.Button(card, text="REGISTRARSE Y VALIDAR DESCUENTO", style="Action.TButton", command=lambda: self.controller.mostrar_frame("Registro"))
        btn_registro.grid(row=row_start+8, column=0, pady=(0, 0))

    def procesar_login(self):
        """Lee campos de entrada, valida hash, y redirecciona al perfil correspondiente."""
        correo = self.ent_correo.get().strip()
        contrasena = self.ent_pass.get().strip()

        if not correo or not contrasena:
            messagebox.showwarning("Atencion", "Todos los campos de acceso son obligatorios.")
            return

        # Buscar usuario en la base de datos
        usuario_encontrado = None
        for usr in self.controller.data_manager.usuarios.values():
            if usr.correo == correo.lower():
                usuario_encontrado = usr
                break

        if usuario_encontrado and usuario_encontrado.iniciar_sesion(contrasena):
            self.controller.usuario_actual = usuario_encontrado
            
            if usuario_encontrado.tipo_usuario == "Administrador":
                self.controller.mostrar_frame("Admin")
            else:
                self.controller.mostrar_frame("Dashboard")
        else:
            messagebox.showerror("Acceso Denegado", "El correo electronico o contrasena son invalidos.")

    def al_mostrar(self):
        """Limpia el password al volver."""
        self.ent_pass.delete(0, tk.END)


# PANTALLA 2: REGISTRO Y VINCULACION DE DESCUENTO ESTUDIANTIL BUAP/TEC/IPN

class RegistroFrame(tk.Frame):
    """Pantalla para el registro de nuevos usuarios con verificacion SEP de matriculas."""
    def __init__(self, parent: tk.Frame, controller: TransporteApp):
        super().__init__(parent, bg=COLOR_BG_PRINCIPAL)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = tk.Frame(self, bg=COLOR_CARD, bd=1, highlightbackground=COLOR_PRIMARIO, highlightthickness=1)
        card.grid(row=0, column=0, padx=20, pady=20, ipadx=30, ipady=30)
        card.grid_columnconfigure(0, weight=1)

        # Cargar logo de la app
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        self.img_logo_tk = None
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((70, 70), Image.Resampling.LANCZOS)
                self.img_logo_tk = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error cargando logo en GUI: {e}")

        if self.img_logo_tk:
            lbl_logo = tk.Label(card, image=self.img_logo_tk, bg=COLOR_CARD)
            lbl_logo.grid(row=0, column=0, pady=(0, 10))
            row_start = 1
        else:
            row_start = 0

        lbl_titulo = ttk.Label(card, text="REGISTRO METROPOLITANO", style="CardTitle.TLabel", font=("Segoe UI", 14, "bold"))
        lbl_titulo.grid(row=row_start, column=0, pady=(0, 15))

        # Campos basicos
        lbl_nombre = ttk.Label(card, text="Nombre Completo (como aparece en matricula)", style="Card.TLabel")
        lbl_nombre.grid(row=row_start+1, column=0, sticky="w", pady=(5, 2))
        self.ent_nombre = ttk.Entry(card, width=32, font=("Segoe UI", 10))
        self.ent_nombre.grid(row=row_start+2, column=0, pady=(0, 10))

        lbl_correo = ttk.Label(card, text="Correo Electronico Institucional", style="Card.TLabel")
        lbl_correo.grid(row=row_start+3, column=0, sticky="w", pady=(5, 2))
        self.ent_correo = ttk.Entry(card, width=32, font=("Segoe UI", 10))
        self.ent_correo.grid(row=row_start+4, column=0, pady=(0, 10))

        lbl_pass = ttk.Label(card, text="Asigne una Contrasena", style="Card.TLabel")
        lbl_pass.grid(row=row_start+5, column=0, sticky="w", pady=(5, 2))
        self.ent_pass = ttk.Entry(card, show="*", width=32, font=("Segoe UI", 10))
        self.ent_pass.grid(row=row_start+6, column=0, pady=(0, 10))

        # Seccion Convenio Escolar
        lbl_uni = ttk.Label(card, text="Seleccione su Universidad", style="Card.TLabel")
        lbl_uni.grid(row=row_start+7, column=0, sticky="w", pady=(5, 2))
        self.cmb_uni = ttk.Combobox(card, values=["BUAP", "TEC DE MONTERREY", "IPN", "NINGUNA (REGULAR)"], state="readonly", width=30)
        self.cmb_uni.grid(row=row_start+8, column=0, pady=(0, 10))
        self.cmb_uni.current(0)
        self.cmb_uni.bind("<<ComboboxSelected>>", self.on_school_changed)

        # Campos de Verificacion Estudiantil (BUAP/TEC/IPN)
        self.frame_verificacion = tk.LabelFrame(card, text=" Verificacion de Subsidio SEP (50% Descuento) ", bg=COLOR_CARD, fg=COLOR_TEXTO_BLANCO, padx=10, pady=10)
        self.frame_verificacion.grid(row=row_start+9, column=0, pady=(10, 20), sticky="ew")
        
        lbl_mat = ttk.Label(self.frame_verificacion, text="Matricula / Credencial Escolar", style="Card.TLabel")
        lbl_mat.pack(anchor="w", pady=(0, 2))
        self.ent_matricula = ttk.Entry(self.frame_verificacion, width=28, font=("Segoe UI", 10))
        self.ent_matricula.pack(pady=(0, 5))
        self.ent_matricula.insert(0, "202134567")

        btn_crear = ttk.Button(card, text="VALIDAR Y EXPEDIR TARJETA", style="Accent.TButton", command=self.procesar_registro)
        btn_crear.grid(row=row_start+10, column=0, sticky="ew", pady=(0, 10))

        btn_cancelar = ttk.Button(card, text="VOLVER AL LOGIN", style="Action.TButton", command=lambda: self.controller.mostrar_frame("Login"))
        btn_cancelar.grid(row=row_start+11, column=0, pady=(5, 0))

    def on_school_changed(self, event=None):
        """Muestra u oculta los campos de verificacion segun seleccion."""
        escuela = self.cmb_uni.get()
        if escuela == "NINGUNA (REGULAR)":
            self.frame_verificacion.grid_remove()
        else:
            self.frame_verificacion.grid()

    def procesar_registro(self):
        """Valida dominios, firma tokens SEP y crea el perfil y tarjeta inteligente."""
        nombre = self.ent_nombre.get().strip()
        correo = self.ent_correo.get().strip()
        contrasena = self.ent_pass.get().strip()
        escuela = self.cmb_uni.get()
        matricula = self.ent_matricula.get().strip()

        # 1. Validaciones de Datos Basicos
        if not nombre or not correo or not contrasena:
            messagebox.showwarning("Atencion", "Favor de rellenar todos los campos del formulario de registro.")
            return

        try:
            # 2. Si aplica convenio, auditar vigencia academica
            tipo_desc = "Regular"
            if escuela != "NINGUNA (REGULAR)":
                # Validar dominio de correo oficial
                if not self.controller.discount_validator.validar_correo_institucional(correo, escuela):
                    messagebox.showerror("Validacion Fallida", f"El correo provisto no coincide con el dominio oficial registrado para la {escuela}.")
                    return

                # Validar matricula contra el servidor de control escolar (SEP)
                valido, msg = self.controller.student_verifier.verificar_estudiante(matricula, escuela)
                if not valido:
                    messagebox.showerror("Subsidio Rechazado", f"El validador de control escolar reporto: {msg}")
                    return

                # Firmar convenio digital
                token_firmado = self.controller.student_verifier.firmar_convenio_descuento(matricula, escuela)
                tipo_desc = escuela
                messagebox.showinfo("Convenio Aprobado", f"Validacion SEP Correcta.\nFirmado digitalmente: {token_firmado}\nSubsidio de descuento del 50% habilitado en su cuenta.")

            # 3. Crear Usuario Pasajero
            nuevo_id = max(list(self.controller.data_manager.usuarios.keys())) + 1
            hash_cuerpo = hashlib.sha256(contrasena.encode('utf-8')).hexdigest()
            
            nuevo_pasajero = Pasajero(
                id_usuario=nuevo_id,
                nombre=nombre,
                correo=correo,
                contrasena_hash=hash_cuerpo,
                id_escuela=escuela if escuela != "NINGUNA (REGULAR)" else "Ninguna"
            )

            # 4. Crear Tarjeta Inteligente asociada con saldo inicial de $30.00
            id_t_num = random.randint(1000, 9999)
            prefijo = escuela.split()[0] if escuela != "NINGUNA (REGULAR)" else "REG"
            id_tarjeta_str = f"{prefijo}-{id_t_num}"
            
            nueva_tarjeta = TarjetaMovilidad(
                id_tarjeta=id_tarjeta_str,
                saldo_actual=30.00,
                id_usuario=nuevo_id,
                tipo_descuento=tipo_desc
            )

            # 5. Persistir en base de datos
            self.controller.data_manager.usuarios[nuevo_id] = nuevo_pasajero
            self.controller.data_manager.tarjetas[id_tarjeta_str] = nueva_tarjeta
            self.controller.data_manager.guardar_usuarios()
            self.controller.data_manager.guardar_tarjetas()

            messagebox.showinfo("Expedicion Exitosa", f"¡Cuenta de movilidad expedida con exito!\nTarjeta Nro: {id_tarjeta_str}\nSaldo de Regalo: $30.00 pesos.\nInicie sesion con sus credenciales.")
            self.controller.mostrar_frame("Login")

        except TransporteException as e:
            messagebox.showerror("Error", f"No se pudo registrar la cuenta: {e.mensaje}")
        except Exception as e:
            messagebox.showerror("Error Interno", f"Se presento un fallo no controlado: {e}")

    def al_mostrar(self):
        """Limpia campos de texto."""
        self.ent_nombre.delete(0, tk.END)
        self.ent_correo.delete(0, tk.END)
        self.ent_pass.delete(0, tk.END)


# PANTALLA 3: PORTAL DEL ESTUDIANTE (DASHBOARD)

class DashboardFrame(tk.Frame):
    """Panel del Estudiante/Pasajero: Muestra tarjetas, recargas, Treeviews de gastos y Dijkstra."""
    def __init__(self, parent: tk.Frame, controller: TransporteApp):
        super().__init__(parent, bg=COLOR_BG_PRINCIPAL)
        self.controller = controller

        # Layout con barra lateral y panel de contenido
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=COLOR_CARD, width=320)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(15, 10), pady=15)
        self.sidebar.grid_columnconfigure(0, weight=1)

        lbl_menu = ttk.Label(self.sidebar, text="PORTAL DE PASAJERO", style="CardTitle.TLabel")
        lbl_menu.grid(row=0, column=0, pady=(20, 10))

        # Card de Tarjeta Visual (Aesthetics)
        self.card_visual = tk.Frame(self.sidebar, bg=COLOR_PRIMARIO, bd=0, padx=15, pady=15)
        self.card_visual.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        self.card_visual.grid_columnconfigure(0, weight=1)

        self.lbl_card_univ = tk.Label(self.card_visual, text="BUAP TRANSIT", font=("Segoe UI", 12, "bold"), fg=COLOR_TEXTO_BLANCO, bg=COLOR_PRIMARIO, anchor="w")
        self.lbl_card_univ.grid(row=0, column=0, sticky="w")

        self.lbl_card_num = tk.Label(self.card_visual, text="BUAP-9901", font=("Consolas", 14), fg=COLOR_TEXTO_BLANCO, bg=COLOR_PRIMARIO, anchor="w")
        self.lbl_card_num.grid(row=1, column=0, sticky="w", pady=10)

        self.lbl_card_saldo = tk.Label(self.card_visual, text="$ 150.00 pesos", font=("Segoe UI", 18, "bold"), fg=COLOR_ACCENTO_GOLD, bg=COLOR_PRIMARIO, anchor="w")
        self.lbl_card_saldo.grid(row=2, column=0, sticky="w")

        self.lbl_card_desc = tk.Label(self.card_visual, text="Descuento: BUAP (50%)", font=("Segoe UI", 9, "italic"), fg=COLOR_TEXTO_MUTED, bg=COLOR_PRIMARIO, anchor="w")
        self.lbl_card_desc.grid(row=3, column=0, sticky="w", pady=(5, 0))

        # Formulario de Recarga
        self.frame_recarga = tk.LabelFrame(self.sidebar, text=" Recargar Tarjeta de Movilidad ", bg=COLOR_CARD, fg=COLOR_TEXTO_BLANCO, padx=10, pady=10)
        self.frame_recarga.grid(row=2, column=0, padx=15, pady=15, sticky="ew")
        
        lbl_monto = ttk.Label(self.frame_recarga, text="Monto a Cargar ($ MXN)", style="Card.TLabel")
        lbl_monto.pack(anchor="w", pady=(0, 2))
        
        self.cmb_monto = ttk.Combobox(self.frame_recarga, values=["$20.00", "$50.00", "$100.00", "$200.00"], state="readonly")
        self.cmb_monto.pack(fill="x", pady=(0, 8))
        self.cmb_monto.current(1)

        btn_recargar = ttk.Button(self.frame_recarga, text="PROCESAR RECARGA", style="Accent.TButton", command=self.procesar_recarga)
        btn_recargar.pack(fill="x", pady=5)

        btn_ver_mapa = ttk.Button(self.sidebar, text="VER SIMULADOR EN VIVO (MAPA)", command=lambda: self.controller.mostrar_frame("Mapa"))
        btn_ver_mapa.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        btn_salir = ttk.Button(self.sidebar, text="CERRAR SESION SEGURO", style="Action.TButton", command=self.cerrar_sesion)
        btn_salir.grid(row=4, column=0, padx=15, pady=(30, 20), sticky="ew")

        self.panel_contenido = tk.Frame(self, bg=COLOR_BG_PRINCIPAL)
        self.panel_contenido.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.panel_contenido.grid_rowconfigure(1, weight=1)
        self.panel_contenido.grid_columnconfigure(0, weight=1)

        # Titulo Bienvenida
        self.lbl_bienvenida = ttk.Label(self.panel_contenido, text="Hola, Alan Garcia Ortiz", style="Title.TLabel")
        self.lbl_bienvenida.grid(row=0, column=0, sticky="w", pady=(10, 20))

        # Notebook (Pestañas)
        self.notebook = ttk.Notebook(self.panel_contenido)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        # PESTAÑA A: HISTORIAL DE VIAJES
        self.tab_viajes = tk.Frame(self.notebook, bg=COLOR_BG_PRINCIPAL)
        self.notebook.add(self.tab_viajes, text=" Historial de Viajes Bimestral ")
        self.tab_viajes.grid_columnconfigure(0, weight=1)
        self.tab_viajes.grid_rowconfigure(0, weight=1)

        # Treeview interactiva
        columnas = ("id", "bus", "fecha", "escuela", "costo")
        self.tree_viajes = ttk.Treeview(self.tab_viajes, columns=columnas, show="headings")
        self.tree_viajes.heading("id", text="Nro Ticket")
        self.tree_viajes.heading("bus", text="Unidad Transportadora")
        self.tree_viajes.heading("fecha", text="Fecha & Hora Abordaje")
        self.tree_viajes.heading("escuela", text="Subsidiador")
        self.tree_viajes.heading("costo", text="Tarifa Descontada")

        self.tree_viajes.column("id", width=80, anchor="center")
        self.tree_viajes.column("bus", width=120, anchor="center")
        self.tree_viajes.column("fecha", width=220, anchor="center")
        self.tree_viajes.column("escuela", width=140, anchor="center")
        self.tree_viajes.column("costo", width=100, anchor="center")
        
        self.tree_viajes.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # PESTAÑA B: PLANIFICADOR DIJKSTRA
        self.tab_planificador = tk.Frame(self.notebook, bg=COLOR_BG_PRINCIPAL)
        self.notebook.add(self.tab_planificador, text=" Planificar Ruta Optima (Dijkstra) ")
        self.tab_planificador.grid_columnconfigure(0, weight=1)
        self.tab_planificador.grid_rowconfigure(1, weight=1)

        # Selector de Estaciones
        frame_routing = tk.Frame(self.tab_planificador, bg=COLOR_CARD, padx=15, pady=15)
        frame_routing.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        lbl_or = ttk.Label(frame_routing, text="Parada Origen", style="Card.TLabel")
        lbl_or.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.cmb_origen = ttk.Combobox(frame_routing, width=28, state="readonly")
        self.cmb_origen.grid(row=1, column=0, padx=5, pady=5)

        lbl_dest = ttk.Label(frame_routing, text="Parada Destino (Transbordo)", style="Card.TLabel")
        lbl_dest.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.cmb_destino = ttk.Combobox(frame_routing, width=28, state="readonly")
        self.cmb_destino.grid(row=1, column=1, padx=5, pady=5)

        btn_trazar = ttk.Button(frame_routing, text="CALCULAR CAMINO CORTO", style="TButton", command=self.procesar_routing)
        btn_trazar.grid(row=1, column=2, padx=15, pady=5)

        # Resultados de Enrutamiento
        self.frame_resultados_routing = tk.LabelFrame(self.tab_planificador, text=" Itinerario de Viaje Sugerido ", bg=COLOR_BG_PRINCIPAL, fg=COLOR_TEXTO_BLANCO, padx=15, pady=15)
        self.frame_resultados_routing.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.txt_itinerario = tk.Text(self.frame_resultados_routing, bg=COLOR_CARD, fg=COLOR_TEXTO_BLANCO, font=("Consolas", 11), wrap="word", state="disabled")
        self.txt_itinerario.pack(fill="both", expand=True)

    def al_mostrar(self):
        """Carga datos del usuario activo en las tarjetas de la GUI y la tabla."""
        usr = self.controller.usuario_actual
        if not usr:
            return

        self.lbl_bienvenida.config(text=f"Bienvenido, {usr.nombre}")
        self.lbl_card_desc.config(text=f"Convenio: {usr.id_escuela} (50% Descuento)" if usr.id_escuela != "Ninguna" else "Convenio: Ninguno (Regular)")

        # Encontrar tarjeta del usuario
        tarjeta = None
        for tj in self.controller.data_manager.tarjetas.values():
            if tj.id_usuario == usr.id_usuario:
                tarjeta = tj
                break

        if tarjeta:
            self.lbl_card_num.config(text=tarjeta.id_tarjeta)
            self.lbl_card_saldo.config(text=f"$ {tarjeta.saldo_actual:.2f} MXN")
            
            # Ajustar estética de tarjeta segun universidad
            if "BUAP" in tarjeta.id_tarjeta:
                self.card_visual.config(bg="#1F3A60")
                self.lbl_card_univ.config(text="BUAP MOBILITY CARD", bg="#1F3A60")
                self.lbl_card_num.config(bg="#1F3A60")
                self.lbl_card_saldo.config(bg="#1F3A60")
                self.lbl_card_desc.config(bg="#1F3A60")
            elif "TEC" in tarjeta.id_tarjeta or "ITESM" in tarjeta.id_tarjeta:
                self.card_visual.config(bg="#27AE60")
                self.lbl_card_univ.config(text="TEC CAMPUS PUEBLA CARD", bg="#27AE60")
                self.lbl_card_num.config(bg="#27AE60")
                self.lbl_card_saldo.config(bg="#27AE60")
                self.lbl_card_desc.config(bg="#27AE60")
            elif "IPN" in tarjeta.id_tarjeta:
                self.card_visual.config(bg="#7D3C98")
                self.lbl_card_univ.config(text="IPN MOBILITY CARD", bg="#7D3C98")
                self.lbl_card_num.config(bg="#7D3C98")
                self.lbl_card_saldo.config(bg="#7D3C98")
                self.lbl_card_desc.config(bg="#7D3C98")
            else:
                self.card_visual.config(bg="#7F8C8D")
                self.lbl_card_univ.config(text="METROPOLITANO PUEBLA CARD", bg="#7F8C8D")
                self.lbl_card_num.config(bg="#7F8C8D")
                self.lbl_card_saldo.config(bg="#7F8C8D")
                self.lbl_card_desc.config(bg="#7F8C8D")

        # Cargar historial en Treeview
        self.tree_viajes.delete(*self.tree_viajes.get_children())
        for v in reversed(usr.historial_viajes):
            self.tree_viajes.insert("", tk.END, values=(
                f"T-{v['id_viaje']}",
                v["id_unidad"],
                v["fecha_hora"],
                v["id_escuela"],
                f"${float(v['costo_aplicado']):.2f}"
            ))

        # Cargar estaciones en los comboboxes de Dijkstra
        router = self.controller.router
        nombres = sorted(list(router.catalogo_estaciones.values()))
        self.cmb_origen.config(values=nombres)
        self.cmb_destino.config(values=nombres)
        if nombres:
            self.cmb_origen.current(0)
            self.cmb_destino.current(len(nombres)-1)

    def procesar_recarga(self):
        """Simula una pasarela de pago y recarga saldo en caliente."""
        usr = self.controller.usuario_actual
        monto_str = self.cmb_monto.get().replace("$", "")
        
        try:
            monto = float(monto_str)
            tarjeta = None
            for tj in self.controller.data_manager.tarjetas.values():
                if tj.id_usuario == usr.id_usuario:
                    tarjeta = tj
                    break
            
            if tarjeta:
                tarjeta.recargar_saldo(monto)
                self.controller.data_manager.guardar_tarjetas()
                self.al_mostrar()
                messagebox.showinfo("Pasarela Bancaria", f"¡Recarga Exitosa!\nSe han abonado ${monto:.2f} pesos a su tarjeta {tarjeta.id_tarjeta} via pasarela virtual segura.")
            else:
                messagebox.showerror("Error", "No se localizo tarjeta de movilidad vinculada a esta cuenta.")
        except Exception as e:
            messagebox.showerror("Fallo Financiero", f"No se pudo completar la transaccion: {e}")

    def procesar_routing(self):
        """Obtiene estaciones de los combos y corre Dijkstra visualizando el paso a paso."""
        orig_nombre = self.cmb_origen.get()
        dest_nombre = self.cmb_destino.get()

        if orig_nombre == dest_nombre:
            messagebox.showwarning("Atencion", "El origen y destino de viaje deben ser paradas diferentes.")
            return

        router = self.controller.router
        
        # Traducir nombres a IDs
        id_orig = -1
        id_dest = -1
        for k, v in router.catalogo_estaciones.items():
            if v == orig_nombre:
                id_orig = k
            if v == dest_nombre:
                id_dest = k

        try:
            camino, km = router.resolver_ruta_corta(id_orig, id_dest)
            
            self.txt_itinerario.config(state="normal")
            self.txt_itinerario.delete("1.0", tk.END)
            
            self.txt_itinerario.insert(tk.END, "============================================================\n")
            self.txt_itinerario.insert(tk.END, f" PLANIFICADOR METROPOLITANO DE RUTAS - ITINERARIO DE VIAJE\n")
            self.txt_itinerario.insert(tk.END, "============================================================\n\n")
            self.txt_itinerario.insert(tk.END, f"Ruta Mas Corta via Red Escolar (Algoritmo de Dijkstra)\n")
            self.txt_itinerario.insert(tk.END, f"Distancia Total Trazada: {km} Kilometros.\n")
            self.txt_itinerario.insert(tk.END, f"Tiempo estimado de arribo a destino: {int(km * 1.8)} minutos.\n\n")
            self.txt_itinerario.insert(tk.END, "SECUENCIA DETALLADA DE TRANSPORTE Y TRANSBORDOS:\n")
            self.txt_itinerario.insert(tk.END, "------------------------------------------------------------\n")
            
            for i, nodo in enumerate(camino):
                parada = router.catalogo_estaciones[nodo]
                # Simular tiempo de espera y congestion
                espera = self.controller.traffic_forecaster.predecir_tiempo_espera(nodo)
                
                if i == 0:
                    self.txt_itinerario.insert(tk.END, f"  [INICIO] Aborde en parada: {parada}\n")
                    self.txt_itinerario.insert(tk.END, f"           -> Espera estimada de bus en anden: {espera} min.\n")
                elif i == len(camino) - 1:
                    self.txt_itinerario.insert(tk.END, f"  [FIN]    Descienda en parada final: {parada}\n")
                else:
                    self.txt_itinerario.insert(tk.END, f"  [CONEXION] Estacion de Transbordo: {parada}\n")
                    self.txt_itinerario.insert(tk.END, f"             -> Tiempo estimado de cambio: {espera} min.\n")
                    
            self.txt_itinerario.insert(tk.END, "\n------------------------------------------------------------\n")
            self.txt_itinerario.insert(tk.END, "* Conserve su saldo de tarjeta para evitar bloqueos de validador en transbordos.")
            self.txt_itinerario.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Ruta Bloqueada", f"No se pudo trazar itinerario: {e}")

    def cerrar_sesion(self):
        """Termina la sesion del pasajero de forma segura."""
        if self.controller.usuario_actual:
            self.controller.usuario_actual.cerrar_sesion()
        self.controller.usuario_actual = None
        self.controller.mostrar_frame("Login")


# PANTALLA 4: MAPA EN VIVO DEL SIMULADOR INTERACTIVO

class LiveMapFrame(tk.Frame):
    """
    Canvas interactivo donde se cargan los mapas PNG programados
    y se plotean los buses moviendose segundo a segundo con el SimulationEngine.
    """
    def __init__(self, parent: tk.Frame, controller: TransporteApp):
        super().__init__(parent, bg=COLOR_BG_PRINCIPAL)
        self.controller = controller

        # Coordenadas relativas de las paradas sobre el Canvas (escalado de imagenes)
        # Permite graficar a los buses interpolados
        self.paradas_canvas_coords: Dict[int, Tuple[int, int]] = {
            101: (150, 120),  # Carolino
            102: (250, 240),  # CCU
            103: (180, 420),  # CU BUAP
            104: (450, 110),  # Amalucan
            
            201: (620, 440),  # Tec Puebla
            202: (580, 250),  # Angelopolis
            203: (780, 120),  # Cholula Tec
            204: (500, 520),  # Lomas
            205: (410, 310),  # Plaza Dorada
            
            301: (950, 500),  # IPN Puebla
            302: (820, 380),  # Paseo Destino IPN
            303: (750, 450),  # San Manuel IPN
            304: (900, 210)   # Cholula IPN
        }

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        frame_top = tk.Frame(self, bg=COLOR_CARD, padx=10, pady=10)
        frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        lbl_titulo = ttk.Label(frame_top, text="SIMULADOR TRANSIT EN VIVO", style="CardTitle.TLabel")
        lbl_titulo.pack(side="left", padx=10)

        # Selector de Universidad activa
        self.cmb_filtro_mapa = ttk.Combobox(frame_top, values=["BUAP", "TEC DE MONTERREY", "IPN"], state="readonly", width=18)
        self.cmb_filtro_mapa.pack(side="left", padx=15)
        self.cmb_filtro_mapa.current(0)
        self.cmb_filtro_mapa.bind("<<ComboboxSelected>>", self.on_cambiar_mapa)

        btn_refrescar = ttk.Button(frame_top, text="ACTUALIZAR GEOLOCALIZACION", style="Action.TButton", command=self.redibujar_elementos)
        btn_refrescar.pack(side="left", padx=10)

        btn_volver = ttk.Button(frame_top, text="VOLVER AL PORTAL", style="TButton", command=self.volver_atras)
        btn_volver.pack(side="right", padx=10)

        # Contenedor central (Canvas de Graficado)
        self.canvas = tk.Canvas(self, bg=COLOR_BG_PRINCIPAL, bd=0, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Referencias de Imagenes cargadas
        self.img_mapa_tk: Optional[ImageTk.PhotoImage] = None

    def al_mostrar(self):
        """Carga el mapa correspondiente a la universidad seleccionada."""
        self.on_cambiar_mapa()

    def volver_atras(self):
        """Redirecciona segun el tipo de usuario logueado."""
        usr = self.controller.usuario_actual
        if usr and usr.tipo_usuario == "Administrador":
            self.controller.mostrar_frame("Admin")
        else:
            self.controller.mostrar_frame("Dashboard")

    def on_cambiar_mapa(self, event=None):
        """Carga la imagen PNG de assets y redibuja estaciones y buses."""
        seleccion = self.cmb_filtro_mapa.get()
        
        # Determinar ruta de archivo de mapa
        nombre_mapa = "buap_route.png"
        if seleccion == "TEC DE MONTERREY":
            nombre_mapa = "tec_route.png"
        elif seleccion == "IPN":
            nombre_mapa = "ipn_route.png"

        ruta_mapa = os.path.join(self.controller.stats.dataset_historico is not None and BASE_DIR or BASE_DIR, "assets", nombre_mapa)

        if os.path.exists(ruta_mapa):
            try:
                # Cargar imagen y escalarla
                img = Image.open(ruta_mapa)
                img = img.resize((1140, 580), Image.Resampling.LANCZOS)
                self.img_mapa_tk = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error cargando imagen de mapa: {e}")
                self.img_mapa_tk = None
        else:
            self.img_mapa_tk = None

        self.redibujar_elementos()

    def redibujar_elementos(self):
        """Limpia el Canvas y vuelve a trazar el mapa base, las estaciones y buses en movimiento."""
        self.canvas.delete("all")

        # 1. Dibujar el mapa de fondo
        if self.img_mapa_tk:
            self.canvas.create_image(0, 0, image=self.img_mapa_tk, anchor="nw")
        else:
            # Fondo alternativo de vector si el asset no se encuentra cargado
            self.canvas.create_rectangle(0, 0, 1140, 580, fill="#2C3E50")
            self.canvas.create_text(570, 290, text="[Mapa no disponible - Assets faltantes]", fill=COLOR_TEXTO_MUTED, font=("Segoe UI", 14))

        # 2. Obtener filtro de universidad activa
        universidad_activa = self.cmb_filtro_mapa.get()

        # 3. Dibujar Estaciones / Paradas asociadas a esta Universidad
        for r_id, ruta in self.controller.data_manager.rutas.items():
            if ruta.universidad_afiliada == universidad_activa:
                # Trazar lineas de trayecto entre paradas
                for i in range(len(ruta.lista_estaciones) - 1):
                    e1 = ruta.lista_estaciones[i]
                    e2 = ruta.lista_estaciones[i+1]
                    
                    if e1.id_estacion in self.paradas_canvas_coords and e2.id_estacion in self.paradas_canvas_coords:
                        x1, y1 = self.paradas_canvas_coords[e1.id_estacion]
                        x2, y2 = self.paradas_canvas_coords[e2.id_estacion]
                        self.canvas.create_line(x1, y1, x2, y2, fill=COLOR_PRIMARIO, width=3, dash=(4, 4))

                # Dibujar los nodos circulares de las paradas
                for est in ruta.lista_estaciones:
                    if est.id_estacion in self.paradas_canvas_coords:
                        x, y = self.paradas_canvas_coords[est.id_estacion]
                        
                        # Circulo de parada
                        self.canvas.create_oval(x-8, y-8, x+8, y+8, fill=COLOR_BG_PRINCIPAL, outline=COLOR_ACCENTO_GOLD, width=2)
                        
                        # Texto
                        self.canvas.create_text(x, y-18, text=est.nombre_parada, fill=COLOR_TEXTO_BLANCO, font=("Segoe UI", 8, "bold"))

        # 4. Dibujar los Autobuses / Vehiculos en transito sobre la ruta
        for v_id, status in self.controller.sim_engine.sim_status.items():
            ruta = self.controller.data_manager.rutas[status["ruta_id"]]
            
            # Solo mostrar buses que corresponden al mapa filtrado
            if ruta.universidad_afiliada == universidad_activa:
                vehiculo = self.controller.data_manager.vehiculos[v_id]
                idx_orig = status["origen_idx"]
                estaciones = ruta.lista_estaciones
                
                if status["direccion_ida"]:
                    idx_dest = idx_orig + 1
                else:
                    idx_dest = idx_orig - 1
                    
                est_orig = estaciones[idx_orig]
                est_dest = estaciones[idx_dest]
                
                # Obtener coordenadas canvas origen y destino
                if est_orig.id_estacion in self.paradas_canvas_coords and est_dest.id_estacion in self.paradas_canvas_coords:
                    x_o, y_o = self.paradas_canvas_coords[est_orig.id_estacion]
                    x_d, y_d = self.paradas_canvas_coords[est_dest.id_estacion]
                    p = status["progreso"]
                    
                    # Interpolacion lineal (LERP) de geoposicion sobre el canvas
                    x_bus = x_o + (x_d - x_o) * p
                    y_bus = y_o + (y_d - y_o) * p
                    
                    # Color del autobus segun su ocupacion
                    color_aforo = COLOR_ACCENTO_OK
                    vol = vehiculo.monitorear_volumen()
                    if vol == "Sobreocupado":
                        color_aforo = COLOR_ACCENTO_WARN
                    elif vol == "Alto":
                        color_aforo = COLOR_ACCENTO_GOLD

                    # Dibujar Rectangulo/Icono de Autobus
                    self.canvas.create_rectangle(x_bus-12, y_bus-8, x_bus+12, y_bus+8, fill=color_aforo, outline=COLOR_TEXTO_BLANCO, width=1.5)
                    self.canvas.create_text(x_bus, y_bus, text=v_id.split("-")[-1], fill=COLOR_TEXTO_BLANCO, font=("Consolas", 8, "bold"))


# PANTALLA 5: CONSOLE DE ADMINISTRACION Y PANDAS ANALYTICS

class AdminFrame(tk.Frame):
    """Panel del Administrador: Visualiza sobrecupos, despacha apoyos, y renderiza Matplotlib."""
    def __init__(self, parent: tk.Frame, controller: TransporteApp):
        super().__init__(parent, bg=COLOR_BG_PRINCIPAL)
        self.controller = controller

        # Layout con barra lateral y panel analitico
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=COLOR_CARD, width=320)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(15, 10), pady=15)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(2, weight=1)

        lbl_menu = ttk.Label(self.sidebar, text="CONSOLA ADMINISTRATIVA", style="CardTitle.TLabel")
        lbl_menu.grid(row=0, column=0, pady=(20, 10))

        # Acciones Rapidas
        btn_sim_map = ttk.Button(self.sidebar, text="MODULO SIMULADOR MAPA", command=lambda: self.controller.mostrar_frame("Mapa"))
        btn_sim_map.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        # Bitacora de Alertas en Caliente (Listbox)
        self.frame_alertas = tk.LabelFrame(self.sidebar, text=" Bitacora de Alertas de Sobrecupo ", bg=COLOR_CARD, fg=COLOR_TEXTO_BLANCO, padx=10, pady=10)
        self.frame_alertas.grid(row=2, column=0, padx=15, pady=15, sticky="nsew")
        self.frame_alertas.grid_columnconfigure(0, weight=1)
        self.frame_alertas.grid_rowconfigure(0, weight=1)

        self.lst_alertas = tk.Listbox(self.frame_alertas, bg=COLOR_BG_PRINCIPAL, fg=COLOR_TEXTO_BLANCO, font=("Segoe UI", 9), bd=0, highlightthickness=0)
        self.lst_alertas.grid(row=0, column=0, sticky="nsew")

        btn_auxiliar = ttk.Button(self.frame_alertas, text="DESPACHAR REFUERZO AUXILIAR", style="Accent.TButton", command=self.despachar_apoyo)
        btn_auxiliar.grid(row=1, column=0, pady=(10, 0), sticky="ew")

        btn_salir = ttk.Button(self.sidebar, text="CERRAR SESION SEGURO", style="Action.TButton", command=self.cerrar_sesion)
        btn_salir.grid(row=3, column=0, padx=15, pady=(20, 20), sticky="ew")

        self.panel_derecho = tk.Frame(self, bg=COLOR_BG_PRINCIPAL)
        self.panel_derecho.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.panel_derecho.grid_columnconfigure(0, weight=1)
        self.panel_derecho.grid_rowconfigure(1, weight=1)

        # Titulo
        self.lbl_titulo = ttk.Label(self.panel_derecho, text="ANALITICA BIMESTRAL DE TRANSPORTE", style="Title.TLabel")
        self.lbl_titulo.grid(row=0, column=0, sticky="w", pady=(10, 10))

        # Contenedor para Grafico Matplotlib
        self.frame_grafico = tk.Frame(self.panel_derecho, bg=COLOR_CARD, bd=0)
        self.frame_grafico.grid(row=1, column=0, sticky="nsew", pady=10)
        self.frame_grafico.grid_rowconfigure(0, weight=1)
        self.frame_grafico.grid_columnconfigure(0, weight=1)

    def al_mostrar(self):
        """Forza a Pandas a cargar y exportar graficas del dataset historico, mostrandola."""
        self.lst_alertas.delete(0, tk.END)
        self.lst_alertas.insert(tk.END, "Iniciando monitoreo de red...")

        # 1. Ejecutar Analisis Pandas/Matplotlib
        self.controller.stats.cargar_dataset()
        ruta_chart = self.controller.stats.graficar_uso_bimestral()

        # 2. Renderizar el grafico en la interfaz usando el canvas de Tkinter
        # Limpiar frame de graficas
        for widget in self.frame_grafico.winfo_children():
            widget.destroy()

        if MATPLOTLIB_CANVAS_AVAILABLE and self.controller.stats.dataset_historico is not None:
            try:
                # Cargar imagen compuestas de Matplotlib
                img_path = os.path.join(CHARTS_DIR, "analisis_bimestral.png")
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    img = img.resize((780, 480), Image.Resampling.LANCZOS)
                    self.img_chart_tk = ImageTk.PhotoImage(img)
                    
                    lbl_chart = tk.Label(self.frame_grafico, image=self.img_chart_tk, bg=COLOR_CARD)
                    lbl_chart.pack(fill="both", expand=True)
                else:
                    self.mostrar_placeholder_grafico()
            except Exception as e:
                print(f"Error cargando grafico en GUI: {e}")
                self.mostrar_placeholder_grafico()
        else:
            self.mostrar_placeholder_grafico()

    def mostrar_placeholder_grafico(self):
        lbl_err = tk.Label(self.frame_grafico, text="Grafica no disponible.\nAsegurese de que Pandas, Matplotlib y Pillow esten correctamente instalados.", fg=COLOR_TEXTO_MUTED, bg=COLOR_CARD, font=("Segoe UI", 12))
        lbl_err.pack(fill="both", expand=True)

    def agregar_alerta(self, mensaje: str):
        """Inserta alertas flotantes en el listbox lateral."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.lst_alertas.insert(0, f"[{timestamp}] {mensaje}")

    def despachar_apoyo(self):
        """Despacha un autobus para liberar sobrecupos."""
        despachados = 0
        for v_id, veh in self.controller.data_manager.vehiculos.items():
            if veh.pasajeros_actuales > veh.capacidad_max:
                res = self.controller.usuario_actual.atender_alerta_sobrecupo(veh)
                self.agregar_alerta(res)
                despachados += 1

        if despachados > 0:
            self.controller.data_manager.guardar_vehiculos()
            messagebox.showinfo("Consola Despachos", f"¡Auxilio Exitoso!\nSe han despachado {despachados} buses de refuerzo temporal para desahogar las estaciones saturadas.")
        else:
            messagebox.showinfo("Consola Despachos", "No se registran unidades saturadas o con sobrecupo de pasajeros en este momento.")

    def cerrar_sesion(self):
        """Cierra sesion de administrador."""
        if self.controller.usuario_actual:
            self.controller.usuario_actual.cerrar_sesion()
        self.controller.usuario_actual = None
        self.controller.mostrar_frame("Login")


# DISPARADOR PRINCIPAL DE LA APLICACION GUI

if __name__ == "__main__":
    # Iniciar la aplicacion de escritorio
    app = TransporteApp()
    app.mainloop()
