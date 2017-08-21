from django.contrib.auth.models import User
from collections import OrderedDict


def get_demographics():
    # Initialize default values
    EDUCATION_LABELS = ["Unknown", "Doctorate", "Masters", "Bachelors degree", "Associate",
                        "Secondary", "Junior secondary", "Elementary", "None", "Other"]
    age_distribution = OrderedDict([
        ('Unknown', 0),
        ('1-15', 0),
        ('16-25', 0),
        ('26-40', 0),
        ('41-above', 0)
    ])
    education_distribution = OrderedDict([
        ('unknown', 0),
        ('p', 0),
        ('m', 0),
        ('b', 0),
        ('a', 0),
        ('hs', 0),
        ('jhs', 0),
        ('el', 0),
        ('none', 0),
        ('other', 0)
    ])
    gender_distribution = OrderedDict([
        ('Unknown', 0),
        ('m', 0),
        ('f', 0),
        ('o', 0)
    ])
    # Get all the active users
    users = User.objects.filter(is_active=True)

    # Filter the users
    for user in users:
        # Filter by age
        if user.profile.age == None:
            age_distribution['Unknown'] += 1
        elif user.profile.age > 0 and user.profile.age <= 15:
            age_distribution['1-15'] += 1
        elif user.profile.age > 15 and user.profile.age <= 25:
            age_distribution['16-25'] += 1
        elif user.profile.age > 25 and user.profile.age <= 40:
            age_distribution['26-40'] += 1
        else:
            age_distribution['41-above'] += 1

        # Fitler by education
        if not user.profile.level_of_education:
            education_distribution['unknown'] += 1
        else:
            education_distribution[user.profile.level_of_education] += 1

        # Filter by gender
        if not user.profile.gender:
            gender_distribution['Unknown'] += 1
        else:
            gender_distribution[user.profile.gender] += 1

    return age_distribution, education_distribution, gender_distribution, EDUCATION_LABELS
