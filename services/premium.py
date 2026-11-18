"""Account-bound visual hints only; server checks still authorize Premium access."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.utcoffset() is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


class PremiumState:
    def __init__(self, path, owner, now=None):
        self.path = Path(path)
        self.owner = owner if isinstance(owner, str) and owner.strip() else None
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.pets = {}
        self.seen = set()
        if not self.owner:
            return
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if (not isinstance(data, dict) or data.get('owner') != self.owner
                    or not isinstance(data.get('pets'), dict)
                    or not isinstance(data.get('seen'), list)):
                return
            self.pets = {pet: date for pet, date in data['pets'].items()
                         if isinstance(pet, str) and pet.strip() and _date(date) is not None}
            self.seen = {order for order in data['seen'] if isinstance(order, str) and order.strip()}
        except (OSError, ValueError, UnicodeError):
            pass

    def active(self, pet_id=None):
        if not self.owner:
            return False
        if pet_id is None:
            return any(_date(date) > self.now() for date in self.pets.values())
        if not isinstance(pet_id, str):
            return False
        date = _date(self.pets.get(pet_id))
        return date is not None and date > self.now()

    def record(self, pet_id, result, acknowledge=True):
        """Return a fresh confirmed order; background refresh can leave it unacknowledged."""
        if (not self.owner or not isinstance(pet_id, str) or not pet_id.strip()
                or not isinstance(result, dict)
                or result.get('state') not in ('none', 'creating', 'pending', 'active',
                                              'rejected', 'cancelled', 'expired')):
            return False
        paid = _date(result.get('paid_until'))
        future = paid is not None and paid > self.now()
        if future:
            previous = _date(self.pets.get(pet_id))
            if previous is None or paid >= previous:
                self.pets[pet_id] = result['paid_until']
        elif result['state'] in ('none', 'expired') or not self.active(pet_id):
            self.pets.pop(pet_id, None)
        order = result.get('order_id')
        fresh = (result['state'] == 'active' and future and isinstance(order, str)
                 and bool(order.strip()) and order not in self.seen)
        if fresh and acknowledge:
            self.seen.add(order)
        self._save()
        return fresh

    def retain_pets(self, ids):
        keep = set(ids)
        remaining = {pet: date for pet, date in self.pets.items() if pet in keep}
        if self.pets != remaining:
            self.pets = remaining
            self._save()

    def _save(self):
        if not self.owner:
            return
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.path.parent, prefix=self.path.name + '.', suffix='.tmp',
                    delete=False) as stream:
                temporary = stream.name
                json.dump({'owner': self.owner, 'pets': self.pets, 'seen': sorted(self.seen)}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            pass  # Care and in-session deduplication must survive a cache write failure.
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError:
                    pass
