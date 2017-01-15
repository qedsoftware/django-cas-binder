def get_free_username(original, is_free, limit):
    if is_free(original):
        return original

    for num in range(2, limit):
        username = "{}_{}".format(original, num)
        if is_free(username):
            return username

    raise Exception("Usernames {} and {}_{}-{} are taken".format(
        original, original, 2, limit - 1))
