from django.core.management.base import BaseCommand
from posts.recommendations import train_matrix_factorization
import time

class Command(BaseCommand):
    help = 'Runs Matrix Factorization training for the Recommendation System.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Recommendation System Training...'))
        start_time = time.time()
        
        try:
            train_matrix_factorization()
            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f'Training Completed Successfully in {elapsed:.2f} seconds.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Training Failed: {e}'))
