from django.db import models

class SubscriptionPlan(models.Model):
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_cycle = models.CharField(
        max_length=50, 
        choices=BILLING_CYCLE_CHOICES, 
        default='monthly'
    )
    discount_offer = models.IntegerField(default=0)  # discount percentage e.g. 0 to 100
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()}) - AU$ {self.price}"
