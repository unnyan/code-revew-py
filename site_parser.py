import requests
from bs4 import BeautifulSoup
import psycopg2

DB_HOST = "postgres"
DB_NAME = "recipe_diet_bot"
DB_USER = "anyta"
DB_PASSWORD = "5665"


def get_connection():
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return connection
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None


def create_table():
    connection = get_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    calories_per_100g INT,
                    ingredients TEXT,
                    instructions TEXT,
                    link TEXT,
                    image_url TEXT,
                    meal_type TEXT
                );
            ''')
            connection.commit()
            print("Таблица создана или уже существует.")
        except Exception as e:
            print(f"Ошибка при создании таблицы: {e}")
        finally:
            cursor.close()
            connection.close()

def drop_table():
    connection = get_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('DROP TABLE IF EXISTS recipes;')
            connection.commit()
            print("Таблица удалена.")
        except Exception as e:
            print(f"Ошибка при удалении таблицы: {e}")
        finally:
            cursor.close()
            connection.close()


def parse_recipes(url, meal_type):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    recipes = []
    for item in soup.select('article.post-card-in-lst.row.no-gutters'):
        try:
            name_tag = item.select_one('h5.hdr a')
            name = name_tag.get_text(strip=True) if name_tag else "Название отсутствует"
            link = name_tag['href'] if name_tag else "Ссылка отсутствует"
            image_tag = item.select_one('span[itemprop="image"] meta[itemprop="contentUrl"]')
            image_url = image_tag['content'] if image_tag else "Изображение отсутствует"
            calories_tag = item.select_one('li.nutrition .calories')
            calories = int(calories_tag.get_text(strip=True)) if calories_tag else 0
            ingredients = ", ".join([
                f"{li.select_one('.name').get_text(strip=True)} {li.select_one('.value').get_text(strip=True)}{li.select_one('.type').get_text(strip=True)}"
                for li in item.select('ul.ingredients-lst li')
                if li.select_one('.name') and li.select_one('.value') and li.select_one('.type')
            ])
            instructions_tag = item.select_one('div.part-1')
            instructions = instructions_tag.get_text(strip=True) if instructions_tag else "Инструкции отсутствуют"
            recipes.append((name, calories, ingredients, instructions, link, image_url, meal_type))
        except Exception as e:
            print(f"Ошибка при парсинге рецепта: {e}")
    return recipes


def save_recipes(recipes):
    connection = get_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.executemany('''
                INSERT INTO recipes (name, calories_per_100g, ingredients, instructions, link, image_url, meal_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            ''', recipes)
            connection.commit()
            print(f"Добавлено {len(recipes)} рецептов.")
        except Exception as e:
            print(f"Ошибка при сохранении рецептов: {e}")
        finally:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    create_table()

    meal_urls = {
        "breakfast": "https://menunedeli.ru/zavtrak/",
        "lunch": "https://menunedeli.ru/chto-prigotovit-na-obed-bystro-i-vkusno/",
        "snack": "https://menunedeli.ru/chto-prigotovit-na-poldnik/",
        "dinner": "https://menunedeli.ru/chto-prigotovit-na-obed-i-uzhin/chto-prigotovit-na-uzhin-dlya-vsej-semi-bystro-i-vkusno/"
    }

    for meal_type, url in meal_urls.items():
        print(f"Парсинг раздела: {meal_type}")
        recipes = parse_recipes(url, meal_type)
        save_recipes(recipes)
        print(f"Готово для {meal_type}.")
