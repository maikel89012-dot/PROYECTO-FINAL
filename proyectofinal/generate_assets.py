import os
from PIL import Image, ImageDraw, ImageFont

def create_university_map(university_name, routes_config, output_path):
    """
    Generates a beautiful, high-tech dark map for a university route system.
    
    university_name: str (e.g., 'BUAP', 'Tec de Monterrey', 'IPN')
    routes_config: list of dicts, each with name, color, and coordinates list
    output_path: str, where to save the image
    """
    # Create a blank image with a dark, premium slate color
    width, height = 800, 450
    bg_color = (26, 36, 43)  # Deep slate gray #1A242B
    image = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Draw a subtle grid system for the map background
    grid_color = (38, 50, 56)
    grid_size = 40
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
    # Draw stylized secondary background "streets" in a light gray/blue
    street_color = (48, 64, 74)
    streets = [
        [(50, 100), (750, 100)],
        [(50, 220), (750, 220)],
        [(50, 350), (750, 350)],
        [(150, 50), (150, 400)],
        [(400, 50), (400, 400)],
        [(650, 50), (650, 400)],
        # Diagonal bypasses
        [(50, 50), (750, 400)],
        [(750, 50), (50, 400)]
    ]
    for street in streets:
        draw.line(street, fill=street_color, width=4)

    # Draw the specific routes with glowing transparency (simulated via multiple widths)
    for route in routes_config:
        color = route["color"]
        coords = route["coords"]
        name = route["name"]
        
        # Draw glow effect (semi-transparent wider lines)
        glow_color = (color[0], color[1], color[2], 50)
        draw.line(coords, fill=glow_color, width=10, joint="round")
        # Draw the main solid route line
        draw.line(coords, fill=color, width=4, joint="round")
        
        # Draw stations/stops along the route
        for i, coord in enumerate(coords):
            # Outer white circle, inner route color circle
            draw.ellipse([coord[0]-6, coord[1]-6, coord[0]+6, coord[1]+6], fill=(255, 255, 255))
            draw.ellipse([coord[0]-4, coord[1]-4, coord[0]+4, coord[1]+4], fill=color)
            
            # Label first and last station
            if i == 0 or i == len(coords) - 1:
                lbl = "Inicio" if i == 0 else "Fin"
                draw.rectangle([coord[0]-25, coord[1]-20, coord[0]+25, coord[1]-6], fill=(44, 62, 80))
                draw.text((coord[0]-18, coord[1]-18), lbl, fill=(255, 255, 255))

    # Add header card
    draw.rectangle([20, 20, 340, 80], fill=(22, 160, 133, 230), outline=(26, 188, 156), width=2)
    
    # Try to use a nice font or default if not available
    try:
        font_title = ImageFont.load_default()
    except Exception:
        font_title = None

    draw.text((35, 30), f"RUTAS CONECTIVIDAD {university_name}", fill=(255, 255, 255))
    draw.text((35, 52), f"Zona Metropolitana de Puebla - 50% Descuento", fill=(241, 196, 15))

    # Save to disk
    image.save(output_path, "PNG")
    print(f"Generated successfully: {output_path}")

def generate_all():
    # Make sure assets folder exists
    os.makedirs(os.path.join("E:\\proyectos\\proyectofinal", "assets"), exist_ok=True)
    
    # Tec de Monterrey coordinates (approx matching the prompt photo)
    tec_routes = [
        {
            "name": "Ruta Azul (Cholula - Tec)",
            "color": (41, 128, 185), # Blue
            "coords": [(100, 120), (120, 250), (220, 290), (320, 250)]
        },
        {
            "name": "Ruta Verde (Lomas - Tec)",
            "color": (39, 174, 96), # Green
            "coords": [(420, 80), (380, 140), (320, 180), (320, 250)]
        },
        {
            "name": "Ruta Celeste (Plaza Dorada - Tec)",
            "color": (52, 152, 219), # Light Blue
            "coords": [(650, 100), (550, 180), (450, 260), (320, 250)]
        }
    ]
    create_university_map(
        "TEC DE MONTERREY", 
        tec_routes, 
        os.path.join("E:\\proyectos\\proyectofinal", "assets", "tec_route.png")
    )

    # BUAP coordinates
    buap_routes = [
        {
            "name": "Ruta Verde (Central Abastos - CU)",
            "color": (39, 174, 96), # Green
            "coords": [(450, 40), (420, 120), (470, 200), (500, 320)]
        },
        {
            "name": "Ruta Azul (Cholula - CU)",
            "color": (41, 128, 185), # Blue
            "coords": [(100, 80), (180, 180), (280, 360), (500, 320)]
        },
        {
            "name": "Ruta Amarilla (Casa Blanca - CU)",
            "color": (241, 196, 15), # Yellow
            "coords": [(700, 80), (680, 200), (580, 280), (500, 320)]
        }
    ]
    create_university_map(
        "BUAP", 
        buap_routes, 
        os.path.join("E:\\proyectos\\proyectofinal", "assets", "buap_route.png")
    )

    # IPN coordinates
    ipn_routes = [
        {
            "name": "Ruta Verde (Periferico - IPN)",
            "color": (39, 174, 96), # Green
            "coords": [(600, 20), (650, 150), (550, 320), (350, 380)]
        },
        {
            "name": "Ruta Celeste (San Manuel - IPN)",
            "color": (52, 152, 219), # Light Blue
            "coords": [(500, 120), (450, 200), (380, 280), (350, 380)]
        },
        {
            "name": "Ruta Azul (Cholula - IPN)",
            "color": (41, 128, 185), # Dark Blue
            "coords": [(100, 80), (250, 150), (300, 260), (350, 380)]
        }
    ]
    create_university_map(
        "IPN", 
        ipn_routes, 
        os.path.join("E:\\proyectos\\proyectofinal", "assets", "ipn_route.png")
    )

if __name__ == "__main__":
    generate_all()
