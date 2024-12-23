from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackContext
import psycopg2
import requests
from bs4 import BeautifulSoup
import os

DB_HOST = "postgres"
DB_NAME = "recipe_diet_bot"
DB_USER = "anyta"
#DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PASSWORD = 5665
BOT_TOKEN = os.getenv("BOT_TOKEN")

GENDER, AGE, WEIGHT, HEIGHT, ACTIVITY, DIET = range(6)

gender_keyboard = [['Мужчина', 'Женщина']]
activity_keyboard = [
    ['1.2 (Минимум нагрузок)', '1.375 (Легкие упражнения 1-3 раза в неделю)'],
    ['1.4625 (Умеренные нагрузки 4-5 раз в н.)', '1.55 (Интенсивные тренировки 4-5 раз в н.)'],
    ['1.725 (Тренировки 2 раза в день)', '1.9 (Интенсивные нагрузки 2 раза в день)']
]
diet_keyboard = [
    ['Для похудения', 'Для поддержания веса', 'Для набора массы'],
    ['Изменить данные']
]


def calculate_calories(gender, age, weight, height, activity):
    if gender == "Мужчина":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    return int(bmr * activity)


async def start_message(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Я бот - составитель меню, напиши /start чтобы начать!"
    )

async def change_diet(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Выберите вашу цель или измените данные:",
        reply_markup=ReplyKeyboardMarkup(diet_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return DIET


async def restart_data_input(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text(
        "Для составления полезного рациона нужно узнать немного информации о вас! Выберите ваш пол:",
        reply_markup=ReplyKeyboardMarkup(
            [['Мужчина', 'Женщина']], resize_keyboard=True, one_time_keyboard=True
        )
    )
    return GENDER


async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Справка по командам:\n\n"
        "👉 `/start` — Начать заново и сбросить все данные.\n"
        "👉 `/cancel` — Отменить текущий процесс.\n"
        "👉 `/start_message` — Получить начальное приветственное сообщение.\n\n"
        "Если у вас возникли вопросы, введите `/help`."
    )


async def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Привет, {user_name}! Я помогу вам составить меню. "
        "Но для начала мне нужно узнать немного информации о вас. "
        "Выберите ваш пол:",
        reply_markup=ReplyKeyboardMarkup(
            [['Мужчина', 'Женщина']], one_time_keyboard=True, resize_keyboard=True
        )
    )
    return GENDER


async def gender(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    valid_genders = {"мужчина": "Мужчина", "женщина": "Женщина"}

    if user_input in valid_genders:
        context.user_data['gender'] = valid_genders[user_input]
        await update.message.reply_text("Введите ваш возраст (только число):")
        return AGE
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите пол из предложенных вариантов: Мужчина или Женщина.",
            reply_markup=ReplyKeyboardMarkup(
                [['Мужчина', 'Женщина']], one_time_keyboard=True, resize_keyboard=True
            )
        )
        return GENDER


async def age(update: Update, context: CallbackContext):
    try:
        user_age = int(update.message.text.strip())
        if 10 <= user_age <= 120:
            context.user_data['age'] = user_age
            await update.message.reply_text("Введите ваш вес в кг (например: 70):")
            return WEIGHT
        else:
            await update.message.reply_text(
                "Пожалуйста, введите реальный возраст от 10 до 120 лет."
            )
            return AGE
    except ValueError:
        await update.message.reply_text("Возраст должен быть числом. Попробуйте снова:")
        return AGE


async def weight(update: Update, context: CallbackContext):
    try:
        user_weight = float(update.message.text.strip())
        if 30 <= user_weight <= 300:
            context.user_data['weight'] = user_weight
            await update.message.reply_text("Введите ваш рост в см (например: 170):")
            return HEIGHT
        else:
            await update.message.reply_text(
                "Пожалуйста, введите реальный вес от 30 до 300 кг."
            )
            return WEIGHT
    except ValueError:
        await update.message.reply_text("Вес должен быть числом. Попробуйте снова:")
        return WEIGHT


async def height(update: Update, context: CallbackContext):
    try:
        user_height = float(update.message.text.strip())
        if 100 <= user_height <= 250:
            context.user_data['height'] = user_height
            await update.message.reply_text(
                "Выберите ваш уровень активности:",
                reply_markup=ReplyKeyboardMarkup(activity_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ACTIVITY
        else:
            await update.message.reply_text(
                "Пожалуйста, введите реальный рост (от 100 до 250 см)."
            )
            return HEIGHT
    except ValueError:
        await update.message.reply_text(
            "Рост должен быть числом. Попробуйте снова:"
        )
        return HEIGHT


async def activity(update: Update, context: CallbackContext):
    activity_level = float(update.message.text.split()[0])
    context.user_data['activity'] = activity_level
    user_data = context.user_data
    calories = calculate_calories(
        user_data['gender'], user_data['age'], user_data['weight'], 
        user_data['height'], user_data['activity']
    )
    user_data['base_calories'] = calories

    await update.message.reply_text(
        f"Ваш базовый уровень калорий: {calories} ккал.\n"
        "Теперь выберите вашу цель:",
        reply_markup=ReplyKeyboardMarkup(diet_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return DIET


async def diet_choice(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    if user_input == "Изменить данные":
        return await restart_data_input(update, context)
    target_calories = None
    if user_input == "Для похудения":
        target_calories = int(context.user_data['base_calories'] * 0.85)
    elif user_input == "Для поддержания веса":
        target_calories = int(context.user_data['base_calories'])
    elif user_input == "Для набора массы":
        target_calories = int(context.user_data['base_calories'] * 1.15)
    if target_calories:
        context.user_data['target_calories'] = target_calories
        await update.message.reply_text(
            f"Ваша дневная калорийность: {target_calories} ккал.\nСоставляю меню на день..."
        )
        await get_recipes(update, context)
        return DIET


    await update.message.reply_text(
        "Пожалуйста, выберите один из предложенных вариантов:",
        reply_markup=ReplyKeyboardMarkup(diet_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return DIET




def get_recipe_details(recipe_url):
    try:
        response = requests.get(recipe_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        main_image = soup.find('img', class_='main-img')
        main_image_url = main_image['src'] if main_image else None
        steps = []
        instructions = soup.select('section.instruction li')
        for step in instructions:
            step_text = step.find('div', class_='desc')
            step_text = step_text.get_text(strip=True) if step_text else None
            step_image = step.find('img', class_='instruction-img')
            step_image_url = step_image['src'] if step_image else None
            if step_text:
                steps.append({'text': step_text, 'image': step_image_url})
        return {
            'main_image': main_image_url,
            'steps': steps
        }
    except Exception as e:
        print(f"Ошибка при получении деталей рецепта: {e}")
        return None


def parse_recipes(url, meal_type):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    recipes = []
    for item in soup.select('.post-card-in-lst.row.no-gutters'):
        try:
            name = item.select_one('meta[itemprop="name"]')['content']
            recipe_url = item.select_one('meta[itemprop="url"]')['content']
            calories_text = item.select_one('.nutrition .calories')
            calories = int(calories_text.get_text(strip=True)) if calories_text else None
            recipe_details = get_recipe_details(recipe_url)
            main_image = recipe_details['main_image'] if recipe_details else None
            steps = recipe_details['steps'] if recipe_details else []

            recipes.append({
                'name': name,
                'calories': calories,
                'link': recipe_url,
                'main_image': main_image,
                'steps': steps,
                'meal_type': meal_type
            })
        except Exception as e:
            print(f"Ошибка при парсинге рецепта: {e}")

    return recipes


async def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text("Диалог был отменен. Введите /start для нового начала.")
    return ConversationHandler.END


async def get_recipes(update: Update, context: CallbackContext):
    try:
        user_data = context.user_data
        target_calories = user_data.get('target_calories')

        if not target_calories:
            await update.message.reply_text(
                "Ошибка: Не удалось определить целевые калории. Попробуйте снова с /start."
            )
            return DIET

        meal_ratios = {
            "breakfast": 0.25,
            "lunch": 0.35,
            "snack": 0.15,
            "dinner": 0.25
        }

        meal_type_translation = {
            "breakfast": "Завтрак",
            "lunch": "Обед",
            "snack": "Перекус",
            "dinner": "Ужин"
        }

        connection = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        cursor = connection.cursor()
        cursor.execute("SELECT name, calories_per_100g, meal_type, link FROM recipes;")
        rows = cursor.fetchall()
        connection.close()

        def portion_calories(calories_per_100g, portion_weight):
            return (calories_per_100g * portion_weight) / 100

        selected_menu = {}
        used_recipes = context.user_data.get('used_recipes', set())
        total_calories = 0
        for meal_type, ratio in meal_ratios.items():
            expected_calories = target_calories * ratio
            meal_options = [row for row in rows if row[2] == meal_type and row[0] not in used_recipes]
            if not meal_options:
                continue
            best_match = min(meal_options, key=lambda x: abs(portion_calories(x[1], 200) - expected_calories))
            best_weight = 200
            actual_calories = portion_calories(best_match[1], best_weight)
            used_recipes.add(best_match[0])
            selected_menu[meal_type] = {
                "name": best_match[0],
                "calories": actual_calories,
                "weight": best_weight,
                "link": best_match[3],
                "calories_per_100g": best_match[1]
            }
            total_calories += actual_calories
        error_margin = abs(total_calories - target_calories)

        if error_margin > target_calories * 0.05:
            last_meal_key = list(selected_menu.keys())[-1]
            last_meal = selected_menu[last_meal_key]
            required_calories = target_calories - (total_calories - last_meal['calories'])
            corrected_weight = required_calories * 100 / last_meal['calories_per_100g']
            corrected_weight = max(50, min(corrected_weight, 500))
            corrected_calories = portion_calories(last_meal['calories_per_100g'], corrected_weight)
            selected_menu[last_meal_key]['weight'] = corrected_weight
            selected_menu[last_meal_key]['calories'] = corrected_calories
            total_calories = target_calories
        context.user_data['selected_menu'] = selected_menu
        context.user_data['used_recipes'] = used_recipes
        message = "Ваше меню на день:\n\n"
        for meal_type, meal in selected_menu.items():
            message += (
                f"🍽️ {meal_type_translation[meal_type]}: {meal['name']} "
                f"({meal['calories']:.0f} ккал, {meal['weight']:.0f} г)\n"
            )

        message += f"\nОбщая калорийность: {total_calories:.0f} ккал (Цель: {target_calories} ккал)."

        await update.message.reply_text(message)
        buttons = [[f"Рецепт {i+1}-го блюда"] for i in range(len(selected_menu))]
        buttons.append(["Выбрать диету/Изменить данные"])

        await update.message.reply_text(
            "Выберите рецепт или измените данные:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return DIET

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
        return DIET


async def show_recipe_steps(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    selected_menu = list(context.user_data.get('selected_menu', {}).values())
    if user_input == "Выбрать диету/Изменить данные":
        return await change_diet(update, context)
    if "Рецепт" in user_input:
        try:
            recipe_number = int(user_input.split('-')[0].split()[1]) - 1
            if recipe_number < 0 or recipe_number >= len(selected_menu):
                raise IndexError
            selected_meal = selected_menu[recipe_number]
            recipe_link = selected_meal['link']
            await update.message.reply_text(f"📖 Рецепт: {selected_meal['name']}\n{recipe_link}")
            buttons = [[f"Рецепт {i+1}-го блюда"] for i in range(len(selected_menu))]
            buttons.append(["Выбрать диету/Изменить данные"])
            await update.message.reply_text(
                "Выберите другой рецепт или измените данные:",
                reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            )
            return DIET
        except (ValueError, IndexError):
            await update.message.reply_text("Пожалуйста, выберите рецепт из предложенных кнопок.")
            return DIET

    await update.message.reply_text("Пожалуйста, выберите рецепт или вернитесь к выбору диеты.")
    return DIET


app = Application.builder().token(BOT_TOKEN).build()


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
        ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity)],
        DIET: [
            MessageHandler(filters.Regex("^Выбрать диету/Изменить данные$"), change_diet),
            MessageHandler(filters.Regex("^Изменить данные$"), restart_data_input),
            MessageHandler(filters.Regex("^(Для похудения|Для поддержания веса|Для набора массы)$"), diet_choice),
            MessageHandler(filters.Regex("^Рецепт \\d+-го блюда$"), show_recipe_steps),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", restart_data_input)
    ],
)

app.add_handler(CommandHandler("start_message", start_message))
app.add_handler(conv_handler)
app.add_handler(CommandHandler("help", help_command))

if __name__ == "__main__":
    print("Бот запущен!")
    app.run_polling()