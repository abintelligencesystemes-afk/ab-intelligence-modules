/** @odoo-module **/
/*
 * abrmd_grow_marketing — Widget Owl de pré-visualisation post.
 *
 * V0.1 : affiche le brouillon généré côté wizard, avec un live char count
 * par canal (LinkedIn 3000, Twitter 280, Instagram 2200, etc.). L'édition
 * réelle se fait dans le champ texte natif Odoo ; ce widget overlay ne
 * fait que valider la longueur et signaler les dépassements.
 */
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const CHAR_LIMITS = {
    linkedin: 3000,
    instagram: 2200,
    facebook: 63206,
    twitter: 280,
    youtube: 5000,
    threads: 500,
    tiktok: 2200,
};

class AbrmdGrowPostPreview extends Component {
    static template = "abrmd_grow_marketing.PostPreview";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            canal: "linkedin",
            content: "",
            charLimit: CHAR_LIMITS.linkedin,
            over: false,
        });

        onWillStart(async () => {
            // Lecture config V0.1 — pas de fetch direct OpenAI
            try {
                const enabled = await this.orm.call(
                    "ir.config_parameter",
                    "get_param",
                    ["abrmd_grow_marketing.enabled", "True"],
                );
                this.state.enabled = enabled === "True";
            } catch (e) {
                console.warn("[abrmd_grow_marketing] config load failed", e);
            }
        });
    }

    onCanalChange(ev) {
        const v = ev.target.value;
        this.state.canal = v;
        this.state.charLimit = CHAR_LIMITS[v] || 3000;
        this._recompute();
    }

    onContentChange(ev) {
        this.state.content = ev.target.value;
        this._recompute();
    }

    _recompute() {
        this.state.over = (this.state.content || "").length > this.state.charLimit;
    }
}

registry.category("actions").add("abrmd_grow_marketing.post_preview", AbrmdGrowPostPreview);

export default AbrmdGrowPostPreview;
export { CHAR_LIMITS };
