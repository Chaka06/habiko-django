from django import forms


class StyledTextInput(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class StyledEmailInput(forms.EmailInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
            "autocomplete": "email",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class StyledPasswordInput(forms.PasswordInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
            "autocomplete": "new-password",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class StyledCurrentPasswordInput(forms.PasswordInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
            "autocomplete": "current-password",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
