import uuid
from typing import List

from packages.browser.page import BrowserPage
from packages.schemas.browser_actions import DOMElement, ElementMetadata, PageModel


class PageInspector:
    """
    Safely inspects a browser page and returns a structured PageModel without
    exposing raw HTML or full DOM to the reasoning engine.
    """

    # A static, restricted JS script to extract interactive elements
    # It assigns a temporary attribute 'data-job-agent-id' to elements to track them
    _EXTRACTOR_SCRIPT = """
    () => {
        const elements = [];
        const interactables = document.querySelectorAll(
            'a, button, input, select, textarea, [role="button"], ' +
            '[role="link"], [tabindex]:not([tabindex="-1"])'
        );
        
        let counter = 0;
        for (const el of interactables) {
            if (elements.length >= 400) break; // Bounded extraction
            const rect = el.getBoundingClientRect();
            const isVisible = rect.width > 0 && rect.height > 0 && 
                              window.getComputedStyle(el).visibility !== 'hidden';
            
            if (!isVisible) continue;
            
            const elementId = 'el-' + counter++;
            el.setAttribute('data-job-agent-id', elementId);
            
            const ariaAttr = el.getAttribute('aria-label') || '';
            const placeholderAttr = el.getAttribute('placeholder') || '';
            const idAttr = el.id || '';
            const nameAttr = el.getAttribute('name') || '';
            const valueAttr = el.value || '';

            const tagName = el.tagName.toLowerCase();
            let text = el.innerText || el.value || el.getAttribute('aria-label') || '';
            if (idAttr) {
                const labelEl = document.querySelector('label[for="' + idAttr + '"]');
                if (labelEl) {
                    text = labelEl.innerText + ' ' + text;
                }
            }
            text = text.substring(0, 100).trim();
            
            const isSubmit = text.toLowerCase().includes('submit') || 
                             text.toLowerCase().includes('complete application');
                             
            const typeAttr = el.getAttribute('type') || '';
            const roleAttr = el.getAttribute('role') || '';

            // Extract options for selects
            const optionsList = [];
            if (tagName === 'select') {
                const opts = el.querySelectorAll('option');
                for (let o of opts) {
                    optionsList.push(o.value || o.innerText || '');
                }
            }

            let sensitivity = 'NORMAL';
            const textContent = text.toLowerCase();
            const idAttrLower = idAttr.toLowerCase();
            const nameAttrLower = nameAttr.toLowerCase();

            const combinedContext = textContent + ' ' + idAttrLower + ' ' + nameAttrLower + ' ' + ariaAttr.toLowerCase();

            if (typeAttr.toLowerCase() === 'password' || 
                combinedContext.includes('password') || 
                combinedContext.includes('2fa') || 
                combinedContext.includes('two factor') || 
                combinedContext.includes('two-factor') || 
                combinedContext.includes('otp') ||
                combinedContext.includes('verification code')) {
                sensitivity = 'AUTHENTICATION';
            } else if (combinedContext.includes('ssn') || 
                       combinedContext.includes('social security') || 
                       combinedContext.includes('credit card') ||
                       combinedContext.includes('bank account')) {
                sensitivity = 'SENSITIVE';
            }
            
            elements.push({
                element_id: elementId,
                tag_name: tagName,
                is_visible: true,
                is_interactive: true,
                text: text,
                input_type: typeAttr || null,
                role: roleAttr || null,
                aria_label: ariaAttr || null,
                name: nameAttr || null,
                id_attr: idAttr || null,
                placeholder: placeholderAttr || null,
                value: valueAttr || null,
                options: optionsList,
                is_submit: isSubmit,
                is_required: el.required || el.getAttribute('aria-required') === 'true',
                sensitivity: sensitivity
            });
        }
        return elements;
    }
    """  # noqa: E501

    async def inspect(self, page: BrowserPage) -> PageModel:
        """
        Runs the extraction script and builds the PageModel.
        """
        # We access _page directly since this is an internal component
        raw_elements = await page._page.evaluate(self._EXTRACTOR_SCRIPT)

        dom_elements: List[DOMElement] = []
        for raw in raw_elements:
            metadata = ElementMetadata(
                tag_name=raw["tag_name"],
                is_visible=raw["is_visible"],
                is_interactive=raw["is_interactive"],
                text=raw.get("text"),
                input_type=raw.get("input_type"),
                role=raw.get("role"),
                aria_label=raw.get("aria_label"),
                name=raw.get("name"),
                id_attr=raw.get("id_attr"),
                placeholder=raw.get("placeholder"),
                value=raw.get("value"),
                options=raw.get("options", []),
                is_submit=raw.get("is_submit", False),
                is_required=raw.get("is_required", False),
                sensitivity=raw.get("sensitivity", "NORMAL"),
            )
            dom_elements.append(DOMElement(element_id=raw["element_id"], metadata=metadata))

        url = await page.get_url()
        title = await page.get_title()
        snapshot_id = str(uuid.uuid4())

        return PageModel(snapshot_id=snapshot_id, url=url, title=title, elements=dom_elements)
