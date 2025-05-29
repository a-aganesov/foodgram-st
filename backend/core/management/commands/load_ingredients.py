import json
import os

from django.core.management.base import BaseCommand
from kitchen.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON-файла в базу данных.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='data/ingredients.json',
            help='Путь до JSON-файла с ингредиентами'
        )

    def handle(self, *args, **options):
        path = options['path']

        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'Файл не найден: {path}'))
            return

        with open(path, encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Ошибка разбора JSON: {e}'))
                return

        ingredients = [
            Ingredient(name=item['name'], measurement_unit=item['measurement_unit'])
            for item in data
        ]

        created = Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f'Загружено {len(created)} ингредиентов.'
        ))
