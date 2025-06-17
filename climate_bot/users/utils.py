from .models import TelegramUser

def save_telegram_user(from_user):
    print(from_user)
    
    telegram_id = from_user.id
    first_name = from_user.first_name
    last_name = from_user.last_name
    username = from_user.username

    print(f"Processing user: {first_name} {last_name} ({telegram_id})")

    user, created = TelegramUser.objects.update_or_create(
        telegram_id=telegram_id,
        defaults={
            'user_name' : username,
            'first_name': first_name,
            'last_name': last_name,
        }
    )
    if created:
        print(f"New user created: {first_name} {last_name}")
    else:
        print(f"User updated: {first_name} {last_name}")

def save_users_locations(from_user, location):
    # Get the user's ID
    user_id = from_user
    # Update the user's location in the database
    user, updated = TelegramUser.objects.update_or_create(
        telegram_id=user_id,
        defaults={
            'coordinates': location,
           
        }
    )
    # Check if the location was updated or a new user was created
    if updated:
        print(f"User {user.first_name} {user.last_name} location updated: ({location})")
    else:
        print(f"User {user.first_name} {user.last_name} created with location: ({location})")
