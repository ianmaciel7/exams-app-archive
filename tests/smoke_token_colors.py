"""Chromium CSS color/interaction checks and original reference screenshots."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_token_contrast import SPEC
from render_token_demo import render

# Canvas performs browser color conversion into an 8-bit sRGB sample. The
# unrounded ratio of these actual sampled channels is tested; Python separately
# checks unquantized opaque source tokens.
JS_RATIO = """([a,b])=>{
 const ctx=document.createElement('canvas').getContext('2d',{willReadFrequently:true});
 function l(c){ctx.clearRect(0,0,1,1);ctx.fillStyle='#ff00ff';ctx.fillStyle=c;ctx.fillRect(0,0,1,1);
 const v=Array.from(ctx.getImageData(0,0,1,1).data);
 if(v[3]!==255)throw Error('Expected opaque sampled color: '+c);
 const k=v.slice(0,3).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;});
 return .2126*k[0]+.7152*k[1]+.0722*k[2];}
 const x=l(a),y=l(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}"""

def ratio(page, a,b):
    return page.evaluate(JS_RATIO,[a,b])

def check(page, theme):
    measured=[]
    for section in page.locator("[data-surface]").all():
        bg=section.evaluate("(el)=>getComputedStyle(el).backgroundColor")
        surface=section.get_attribute("data-surface")
        for text in section.locator("[data-token]").all():
            color=text.evaluate("(el)=>getComputedStyle(el).color")
            measured.append({"theme":theme,"surface":surface,"role":text.get_attribute("data-token"),"ratio":ratio(page,color,bg),"min":4.5})
        focus=section.locator("button")
        # Tab modality was established by keyboard. Focus each sample, verify
        # actual outline color and surrounding surface rather than token alone.
        focus.focus()
        expect(focus).to_be_focused()
        outline=focus.evaluate("(el)=>{const s=getComputedStyle(el);return {color:s.outlineColor,width:s.outlineWidth,style:s.outlineStyle}}")
        assert outline["style"]=="solid" and outline["width"]=="3px",outline
        measured.append({"theme":theme,"surface":surface,"role":"focus-visible","ratio":ratio(page,outline["color"],bg),"min":3})
    for chip in page.locator("[data-chip]").all():
        color,bg=chip.evaluate("(el)=>{const s=getComputedStyle(el);return [s.color,s.backgroundColor]}")
        measured.append({"theme":theme,"surface":chip.get_attribute("data-chip"),"role":"chip","ratio":ratio(page,color,bg),"min":4.5})
    return measured

def main(output):
    output.mkdir(parents=True,exist_ok=True)
    html=render(SPEC.read_text(encoding="utf-8"))
    (output/"original-token-demo.html").write_text(html,encoding="utf-8")
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={"width":1024,"height":900},reduced_motion="reduce")
        page.set_content(html)
        page.keyboard.press("Tab")
        expect(page.locator("#theme")).to_be_focused()
        rows=check(page,"light")
        page.screenshot(path=str(output/"light.png"),full_page=True)
        page.locator("#theme").click()
        page.keyboard.press("Tab")
        rows+=check(page,"dark")
        page.screenshot(path=str(output/"dark.png"),full_page=True)
        assert all(x["ratio"]>=x["min"] for x in rows),[x for x in rows if x["ratio"]<x["min"]]
        # Mutation must trigger the same browser check, then restore the CSS.
        page.locator("[data-surface='--surface-panel'] [data-token='--content-primary']").evaluate("(el)=>el.style.color='var(--surface-panel)'")
        mutated=check(page,"dark")
        assert any(x["ratio"]<x["min"] for x in mutated)
        page.set_content(html)
        page.emulate_media(forced_colors="active",reduced_motion="reduce")
        page.set_viewport_size({"width":390,"height":844})
        assert page.evaluate("matchMedia('(forced-colors: active)').matches")
        page.keyboard.press("Tab")
        expect(page.locator("#theme")).to_be_focused()
        assert page.locator("#theme").evaluate("(el)=>getComputedStyle(el).outlineStyle")=="solid"
        page.keyboard.press("Tab")
        expect(page.locator("#select")).to_be_focused()
        page.keyboard.press("Space")
        expect(page.locator("#select")).to_have_attribute("aria-pressed","true")
        expect(page.get_by_role("status")).to_have_text("Selected")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output/"forced-colors-mobile.png"),full_page=True)
        browser.close()
    result={"scope":"original demo only, not active app or full WCAG certification",
            "opaque_rendered_and_composited_pairs":len(rows),
            "failed_pairs":[x for x in rows if x["ratio"]<x["min"]],
            "min_text":min(x["ratio"] for x in rows if x["min"]==4.5),
            "min_focus":min(x["ratio"] for x in rows if x["min"]==3),
            "mutation_detected":True,"forced_colors_keyboard_and_mobile_reflow":True,
            "pairs":rows,"not_tested":["P3 hardware","color-vision simulation","image/gradient backgrounds","other engines","active app"]}
    (output/"token-browser-report.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="pairs"},indent=2))

if __name__=="__main__":
    main(Path(sys.argv[1]))
