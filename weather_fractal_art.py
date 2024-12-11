import pygame
import requests
import numpy as np
import time
import random
import colorsys

# API configuration
API_KEY = "1236163ba879cdc934eac57551308fbe"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather?q={}&appid={}&units=metric"

# Pygame
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Dynamic Weather Fractal Art")

# Fonts
font = pygame.font.Font(None, 24)
large_font = pygame.font.Font(None, 32)

# Cities
cities = ["Tehran,IR", "New York,US", "Tokyo,JP", "London,UK", "Sydney,AU"]

def get_weather_data(city):
    try:
        response = requests.get(BASE_URL.format(city, API_KEY), timeout=10)
        response.raise_for_status()
        data = response.json()
        if all(key in data for key in ['main', 'wind', 'clouds']):
            return data
        else:
            print(f"Error: Missing required data for {city}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching weather data for {city}: {e}")
        return None

def map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

@np.vectorize
def julia_set(z, c, max_iter):
    for n in range(max_iter):
        if abs(z) > 2:
            return n
        z = z*z + c
    return max_iter

def get_fractal_params(weather_data):
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data['wind']['speed']
    clouds = weather_data['clouds']['all']

    zoom = map_value(wind_speed, 0, 20, 0.5, 2.0)
    c_real = map_value(temp, -10, 40, -1, 1)
    c_imag = map_value(humidity, 0, 100, -1, 1)
    max_iter = int(50 + clouds)
    hue_offset = map_value(temp, -10, 40, 0, 1)
    saturation = map_value(humidity, 0, 100, 0.5, 1)
    value = map_value(clouds, 0, 100, 0.5, 1)

    return zoom, c_real, c_imag, max_iter, hue_offset, saturation, value

def create_fractal(width, height, params, time_offset):
    if params is None:
        return None
    zoom, c_real, c_imag, max_iter, hue_offset, saturation, value = params
    
    x = np.linspace(-2, 2, width)
    y = np.linspace(-2, 2, height)
    X, Y = np.meshgrid(x, y)
    Z = X + Y*1j
    
    
    c = complex(c_real + 0.1 * np.sin(time_offset), c_imag + 0.1 * np.cos(time_offset))
    
    fractal = julia_set(Z/zoom, c, max_iter)
    fractal = fractal / np.max(fractal)
    
    hue = (fractal + hue_offset + time_offset * 0.05) % 1
    hsv = np.dstack((hue, np.full_like(hue, saturation), np.full_like(hue, value)))
    
    rgb = np.apply_along_axis(lambda x: colorsys.hsv_to_rgb(*x), 2, hsv)
    return (rgb * 255).transpose(1, 0, 2).astype(np.uint8)

def interpolate_params(params1, params2, t):
    interpolated = [p1 * (1 - t) + p2 * t for p1, p2 in zip(params1, params2)]
    interpolated[3] = int(interpolated[3])  # Ensure max_iter is an integer
    return interpolated

def draw_weather_art(fractal, weather_data, next_weather_data, transition, current_city, next_city):
    if fractal is None:
        screen.fill((0, 0, 0))
    else:
        pygame.surfarray.blit_array(screen, fractal)

    if weather_data and next_weather_data:
        temp = weather_data['main']['temp'] * (1 - transition) + next_weather_data['main']['temp'] * transition
        humidity = weather_data['main']['humidity'] * (1 - transition) + next_weather_data['main']['humidity'] * transition
        wind_speed = weather_data['wind']['speed'] * (1 - transition) + next_weather_data['wind']['speed'] * transition
        clouds = weather_data['clouds']['all'] * (1 - transition) + next_weather_data['clouds']['all'] * transition

        info_texts = [
            f"Temperature: {temp:.1f}°C",
            f"Humidity: {humidity:.1f}%",
            f"Wind Speed: {wind_speed:.1f} m/s",
            f"Cloud Cover: {clouds:.1f}%"
        ]
        
        for i, text in enumerate(info_texts):
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (10, height - 100 + i * 25))

    city_text = large_font.render(f"Transitioning: {current_city} -> {next_city}", True, (255, 255, 255))
    screen.blit(city_text, (10, 10))

    pygame.display.flip()

def main():
    clock = pygame.time.Clock()
    
    def get_next_valid_city(current_index):
        for i in range(len(cities)):
            index = (current_index + i) % len(cities)
            data = get_weather_data(cities[index])
            if data:
                return index, data
        return None, None

    current_index, current_weather_data = get_next_valid_city(0)
    if current_index is None:
        print("Error: Unable to fetch valid weather data for any city.")
        return

    next_index, next_weather_data = get_next_valid_city(current_index + 1)
    if next_index is None:
        print("Error: Unable to fetch valid weather data for a second city.")
        return

    current_params = get_fractal_params(current_weather_data)
    next_params = get_fractal_params(next_weather_data)
    
    transition_duration = 10  # seconds
    transition_start = time.time()
    start_time = time.time()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        current_time = time.time()
        time_offset = current_time - start_time
        transition = min(1, (current_time - transition_start) / transition_duration)
        
        interpolated_params = interpolate_params(current_params, next_params, transition)
        fractal = create_fractal(width, height, interpolated_params, time_offset)
        
        draw_weather_art(fractal, current_weather_data, next_weather_data, transition, 
                         cities[current_index].split(',')[0], cities[next_index].split(',')[0])

        if transition >= 1:
            current_index, current_weather_data = next_index, next_weather_data
            current_params = next_params
            next_index, next_weather_data = get_next_valid_city(current_index + 1)
            if next_index is None:
                print("Error: No more valid cities available. Exiting.")
                running = False
            else:
                next_params = get_fractal_params(next_weather_data)
                transition_start = current_time

        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()