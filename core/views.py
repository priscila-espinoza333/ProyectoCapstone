from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def index(request):
    return render(request, 'core/index.html')

def canchas(request):
    tipos_canchas = [
        {"nombre": "Fútbol", "descripcion": "Canchas de fútbol 5 y fútbol 7"},
        {"nombre": "Tenis", "descripcion": "Canchas rápidas y de arcilla"},
        {"nombre": "Pádel", "descripcion": "Canchas dobles con muros de vidrio"},
        {"nombre": "Básquetbol", "descripcion": "Canchas techadas y abiertas"},
    ]
    return render(request, 'core/canchas.html', {"tipos_canchas": tipos_canchas})

def canchas_futbol(request):
    canchas = [
        {
            "nombre": "Cancha Fútbol 1",
            "descripcion": "Cancha con pasto sintético de alta calidad.",
            "medidas": "40m x 20m",
            "precio": "$25.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1608152681997-3d4cbd07d4bc?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Fútbol 2",
            "descripcion": "Ideal para partidos recreativos y entrenamientos.",
            "medidas": "35m x 18m",
            "precio": "$20.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1609782354937-3f5649862e4e?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Fútbol 3",
            "descripcion": "Cuenta con iluminación LED para juegos nocturnos.",
            "medidas": "45m x 25m",
            "precio": "$30.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1578390433457-8d81e43655dc?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Fútbol 4",
            "descripcion": "Cancha techada para todo clima.",
            "medidas": "38m x 19m",
            "precio": "$28.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1549921296-3a7580470f0b?auto=format&fit=crop&w=800&q=60"
        },
    ]
    return render(request, 'core/canchas_futbol.html', {"canchas": canchas})

def canchas_basquetbol(request):
    canchas = [
        {
            "nombre": "Cancha Básquetbol 1",
            "descripcion": "Cancha techada profesional con piso de madera.",
            "medidas": "28m x 15m",
            "precio": "$30.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1619441207971-b4cbd16db8ee?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Básquetbol 2",
            "descripcion": "Cancha al aire libre ideal para partidos amistosos.",
            "medidas": "26m x 14m",
            "precio": "$25.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1605296867304-46d5465a13f1?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Básquetbol 3",
            "descripcion": "Cancha con iluminación nocturna y graderías.",
            "medidas": "28m x 15m",
            "precio": "$28.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Básquetbol 4",
            "descripcion": "Espacio cerrado para entrenamiento profesional.",
            "medidas": "28m x 14m",
            "precio": "$32.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1622078615930-fd1f645ba76a?auto=format&fit=crop&w=800&q=60"
        },
    ]
    return render(request, 'core/canchas_basquetbol.html', {"canchas": canchas})

def canchas_tenis(request):
    canchas = [
        {
            "nombre": "Cancha Tenis 1",
            "descripcion": "Cancha de arcilla, ideal para juegos lentos y controlados.",
            "medidas": "23.77m x 10.97m",
            "precio": "$22.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1574629810360-7efbbe1956a2?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Tenis 2",
            "descripcion": "Cancha rápida con superficie de cemento.",
            "medidas": "23.77m x 8.23m",
            "precio": "$24.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1611605698335-cf2d608f38a0?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Tenis 3",
            "descripcion": "Cancha techada con iluminación nocturna.",
            "medidas": "23.77m x 10.97m",
            "precio": "$27.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1584944350766-e109f4a36f99?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Tenis 4",
            "descripcion": "Superficie de pasto sintético, ideal para entrenamientos.",
            "medidas": "23.77m x 10.97m",
            "precio": "$25.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1588912437053-3d8464d1306b?auto=format&fit=crop&w=800&q=60"
        },
    ]
    return render(request, 'core/canchas_tenis.html', {"canchas": canchas})

def canchas_padel(request):
    canchas = [
        {
            "nombre": "Cancha Pádel 1",
            "descripcion": "Cancha techada con piso sintético y muros de vidrio.",
            "medidas": "20m x 10m",
            "precio": "$18.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1638287211983-f9e0718a2b6d?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Pádel 2",
            "descripcion": "Ideal para partidos dobles, iluminación LED.",
            "medidas": "20m x 10m",
            "precio": "$20.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1623197314133-6d93c7715d04?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Pádel 3",
            "descripcion": "Cancha al aire libre con reja metálica perimetral.",
            "medidas": "20m x 10m",
            "precio": "$16.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1584626671681-5167765fdb7c?auto=format&fit=crop&w=800&q=60"
        },
        {
            "nombre": "Cancha Pádel 4",
            "descripcion": "Espacio exclusivo para torneos y competencias.",
            "medidas": "20m x 10m",
            "precio": "$22.000 por hora",
            "imagen": "https://images.unsplash.com/photo-1619038138372-2d835a226b27?auto=format&fit=crop&w=800&q=60"
        },
    ]
    return render(request, 'core/canchas_padel.html', {"canchas": canchas})




