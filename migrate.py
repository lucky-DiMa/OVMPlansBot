from classes import PlansBotUser


# User.migrate('notifications', True)
# User.migrate('able_to_change_notifications', False)
# User.migrate('is_owner', False)
# User.migrate('is_admin', False)
PlansBotUser.migrate('admin_permissions.invite_new_users',
                     False)
