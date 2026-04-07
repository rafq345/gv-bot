class NutritionCalculatorService:

    @staticmethod
    def calculate(products):
        total_protein = 0
        total_fat = 0
        total_carbs = 0

        for p in products:
            if p["name"] == "курица":
                total_protein += 25
                total_fat += 5
            if p["name"] == "гречка":
                total_carbs += 30
            if p["name"] == "огурец":
                total_carbs += 5

        return {
            "protein": total_protein,
            "fat": total_fat,
            "carbs": total_carbs
        }

class NutritionService:

    def analyze(self, vision_data):
        # предполагаем, что vision_data — это список продуктов
        # если структура другая — потом поправим

        calculator = NutritionCalculatorService()
        nutrition = calculator.calculate(vision_data)

        return {
            "nutrition": nutrition,
            "comment": "Анализ выполнен"
        }
