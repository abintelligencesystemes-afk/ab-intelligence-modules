# AI RGPD — Conformité complète (6 piliers) pour Odoo 19

> Module Odoo de mise en conformité RGPD complète, par **AB Intelligence Systèmes**.
> Version 0.2.0 — 27 mai 2026 — License **LGPL-3** — gratuit.

## Les 6 piliers

1. **Pilier 1 — Registre des activités de traitement (Article 30 RGPD)**
   Modèle `abrmd.rgpd.registre`. 3 entrées par défaut (CRM, Comptabilité, RH). Import/export CSV natif Odoo.

2. **Pilier 2 — Consentements (Article 7 RGPD)**
   Modèle `abrmd.rgpd.consent`. Capture, retrait, expiration, renouvellement. Hash SHA-256 + sel pour pseudonymisation cross-records. Cron quotidien d'expiration.

3. **Pilier 3 — Droits des personnes (Articles 12-22 RGPD)**
   Modèle `abrmd.rgpd.request`. Workflow complet draft → received → identity_check → in_progress → done/refused. Délais légaux calculés (1 mois + 2 mois prolongation). Cron quotidien d'alerte échéance. 7 types de demandes couverts.

4. **Pilier 4 — Anonymisation et pseudonymisation**
   AbstractModel `abrmd.rgpd.anonymizer`. Server Actions sur `res.partner` (pseudonymiser / anonymiser DÉFINITIVEMENT). Helpers email / phone / IP anonymisation.

5. **Pilier 5 — Logs d'accès**
   Modèle `abrmd.rgpd.access.log`. API `log_access(model, res_id, ...)` callable depuis n'importe quel modèle. Marquage données sensibles. Cron de purge auto au-delà rétention configurée (défaut 5 ans).

6. **Pilier 6 — Dashboard DPO**
   TransientModel `abrmd.rgpd.dashboard`. KPIs en temps réel + alertes (demandes en retard, échéances à 7 jours, contact DPO non configuré, registre vide).

## Installation

```bash
# 1. Drop le module dans ton addons-path
# 2. Update apps list dans Odoo
# 3. Install "AI RGPD" depuis Apps
# 4. Configure le DPO dans Paramètres → AI RGPD
# 5. Active la base.automation pour tracer les accès aux modèles sensibles
```

## Configuration initiale (5 min)

1. **Paramètres → AI RGPD** :
   - Nom + email + téléphone du DPO
   - Sel d'anonymisation (laisser auto-générer si vide)
   - Délai légal demandes (défaut 30 jours)
   - Rétention par défaut (défaut 1095 jours = 3 ans)

2. **Menu AI RGPD → Registre Art.30** :
   - Vérifie les 3 entrées par défaut (CRM, Compta, RH)
   - Adapte le nom du responsable et l'email
   - Ajoute tes traitements spécifiques

3. **Menu AI RGPD → Dashboard DPO** :
   - Vérifie que toutes les alertes sont vertes

## Workflow demande RGPD

Une personne te demande l'accès à ses données ?

1. **Menu AI RGPD → Demandes** → Nouveau
2. Type = "Droit d'accès (Art.15)", saisir le nom + email du demandeur
3. Clic "Marquer reçue" → tu reçois une activité auto "Vérifier identité dans 3 jours"
4. Reçois copie de pièce d'identité par mail, renseigne la méthode de vérification, clic "Identité vérifiée"
5. Prépare la réponse dans l'onglet "Traitement et réponse", joins l'export des données du sujet
6. Clic "Clôturer" — tu es dans les clous Art.12.3

Le cron quotidien `cron_abrmd_rgpd_request_alerts` t'alerte à J-7 et te marque "en retard" si échéance dépassée.

## Anonymisation d'un partenaire

1. Va sur la fiche du `res.partner` à anonymiser
2. Action → "RGPD — Anonymiser DÉFINITIVEMENT (Art.17)" (réservé Manager RGPD)
3. Le partenaire est mis à jour : name = "Anonymisé · ID", email/phone/adresse vidés, comment = horodatage
4. Un log `abrmd.rgpd.access.log` de type `anonymization` est créé automatiquement (preuve d'exécution)

Variante réversible : "Pseudonymiser (réversible)" — hash SHA-256 + sel, permet ré-identification via la clé secrète.

## Tracer un accès depuis un modèle custom

Dans ton code Python :

```python
def export_clients_csv(self):
    self.env["abrmd.rgpd.access.log"].sudo().log_access(
        model="res.partner",
        res_id=False,
        log_type="export",
        description="Export CSV de %d clients" % len(self),
        legal_basis="legitimate_interest",
        sensitive=False,
    )
    # ... ton export ...
```

## Compatibilité

- **Odoo 19** Community et Enterprise (testé 19.2)
- **Dépendances** : `base`, `mail`, `mail_activity` (standards)
- **Pas de dépendance Python externe** — module 100 % stdlib
- **Pas de call-home obligatoire** — télémétrie opt-in via Paramètres

## License

LGPL-3 — utilise, modifie, redistribue librement.
Code source : https://github.com/abintelligencesystemes-afk/ab-intelligence-modules (branche 19.0)

## Support

- Email : contact@rmdsto.re
- Web : https://rmdstore.fr/ai-rgpd
- Issues : https://github.com/abintelligencesystemes-afk/ab-intelligence-modules/issues

---

© 2026 AB Intelligence Systèmes — Anthony Boursier
