from django.db import models

class DealPlan(models.Model):
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
    active_deals_limit = models.IntegerField(default=1, null=True, blank=True, help_text="Set to null or leave blank for unlimited active deals.")
    badge_text = models.CharField(max_length=255, blank=True, null=True)  # e.g. "New Business"
    is_most_popular = models.BooleanField(default=False)
    features = models.JSONField(default=list, blank=True, null=True)  # list of strings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()}) - AU$ {self.price}"


class Deal(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Retail', 'Retail'),
        ('Services', 'Services'),
        ('Beauty', 'Beauty'),
        ('Fitness', 'Fitness'),
        ('Automotive', 'Automotive'),
        ('Home Services', 'Home Services'),
        ('Family', 'Family'),
    ]

    DEAL_TYPE_CHOICES = [
        ('Percentage', 'Percentage'),
        ('Flat Discount', 'Flat Discount'),
        ('Buy One Get One', 'Buy One Get One'),
        ('Other', 'Other'),
    ]

    BUSINESS_TYPE_CHOICES = [
        ('Physical Location', 'Physical Location'),
        ('Online Service', 'Online Service'),
    ]

    creator = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_deals'
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    deal_type = models.CharField(max_length=50, choices=DEAL_TYPE_CHOICES, default='Percentage')
    description = models.TextField(max_length=500)
    
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, default='Physical Location')
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=50)
    website = models.URLField(blank=True, null=True)
    social_links = models.CharField(max_length=255, blank=True, null=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    terms_conditions = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    views_count = models.PositiveIntegerField(default=0)
    call_clicks_count = models.PositiveIntegerField(default=0)
    directions_clicks_count = models.PositiveIntegerField(default=0)
    saves_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.business_name} ({self.category})"


class DealPhoto(models.Model):
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to='deal_photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Deal: {self.deal.title}"


class SavedDeal(models.Model):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='saved_deals'
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'deal')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.deal.title}"

