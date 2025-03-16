from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']  # We want the user to provide a rating and a comment

    # Define the possible choices for the rating field (1 to 5 stars)
    RATING_CHOICES = [(i, f'{i} Star') for i in range(1, 6)]  # This creates choices like (1, "1 Star"), (2, "2 Star")...

    # Create a ChoiceField for rating with a radio button selection style
    rating = forms.ChoiceField(choices=RATING_CHOICES, widget=forms.RadioSelect)