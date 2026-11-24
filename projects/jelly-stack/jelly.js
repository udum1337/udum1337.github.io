/* JellyBody — желе с пружинной деформацией.
 *
 * Почему не свободный Verlet-меш: он гнётся "бананом" и выглядит как
 * кривой полигон. Здесь деформация ограничена естественными степенями
 * свободы желе — сжатие по вертикали и боковой сдвиг верхушки.
 *
 * Каждая из них — пружина с демпфером:
 *   sy   — коэффициент сжатия (1 = норма, 0.7 = сплющено)
 *   shear — насколько верхушка уехала вбок
 *
 * При ударе скорость падения переходит в импульс сжатия → тело
 * плющится и пружинно возвращается с перелётом. Физика настоящая,
 * просто ограничена формой, которую невозможно испортить.
 *
 * Настройки пружины общие с game.js: там она продолжает колебания
 * уже на лежащей желешке, и важно, чтобы числа совпадали.
 */

const SQUASH_K = 70;       // жёсткость: меньше — медленнее и ленивее
const SQUASH_DAMP = 4.2;   // затухание: меньше — дольше дрожит
const SQUASH_MIN = 0.55;   // сильнее не сплющивать
const SQUASH_MAX = 1.35;   // сильнее не растягивать

class JellyBody {
  constructor(scene, x, y, w, h, color) {
    this.color = color;
    this.w = w;
    this.h = h;
    this.x = x;
    this.y = y;

    this.vy = 0;
    this.sy = 1;        // сжатие по вертикали
    this.syVel = 0;
    this.shear = 0;     // боковой сдвиг верхушки
    this.shearVel = 0;

    this.onGround = false;
    this.contact = 0;

    this.graphics = scene.add.graphics();
    this.graphics.setDepth(3);

    this.draw();
  }

  // горизонтальный масштаб: сохраняем объём (сплющили — стало шире)
  get sx() {
    return 1 + (1 - this.sy) * 0.6;
  }

  // точка на контуре "стадиона", u — доля периметра 0..1
  static stadiumPoint(u, w, h) {
    const r = h / 2;
    const sw = Math.max(0, w - 2 * r);
    const arc = Math.PI * r;
    const total = 2 * sw + 2 * arc;
    let d = (((u % 1) + 1) % 1) * total;

    if (d < sw) return { x: -w / 2 + r + d, y: -r };
    d -= sw;

    if (d < arc) {
      const a = -Math.PI / 2 + (d / arc) * Math.PI;
      return { x: w / 2 - r + Math.cos(a) * r, y: Math.sin(a) * r };
    }
    d -= arc;

    if (d < sw) return { x: w / 2 - r - d, y: r };
    d -= sw;

    const a = Math.PI / 2 + (d / arc) * Math.PI;
    return { x: -w / 2 + r + Math.cos(a) * r, y: Math.sin(a) * r };
  }

  step(dt, gravity, surface) {
    // --- падение ---
    this.vy += gravity * dt;
    this.y += this.vy * dt;

    // --- пружина сжатия ---
    // в полёте тело слегка вытягивается, на земле стремится к норме.
    // Пружина мягкая и медленная: сжатие видно глазом, а не проносится
    // за два кадра. Один период ~0.8 сек — отсюда "сочность".
    const target = this.onGround ? 1 : 1 + Math.min(this.vy / 4000, 0.12);
    this.syVel += (-SQUASH_K * (this.sy - target) - SQUASH_DAMP * this.syVel) * dt;
    this.sy += this.syVel * dt;
    this.sy = Math.min(SQUASH_MAX, Math.max(SQUASH_MIN, this.sy));

    // --- боковой сдвиг ---
    this.shearVel += (-90 * this.shear - 5 * this.shearVel) * dt;
    this.shear += this.shearVel * dt;

    // --- удар о поверхность ---
    if (surface && !this.onGround) {
      const halfW = (this.w / 2) * this.sx;
      const left = this.x - halfW;
      const right = this.x + halfW;
      const overlap = Math.min(right, surface.right) - Math.max(left, surface.left);

      // слишком мало перекрытия — пролетаем мимо, как и должно быть
      if (overlap > 34) {
        const bottom = this.y + (this.h / 2) * this.sy;
        if (bottom >= surface.y) {
          this.onGround = true;
          this.contact = 1;

          const impact = Math.min(Math.max(this.vy / 900, 0.3), 1.6);
          // корень: сильные удары не превращают желе в плоский блин
          this.syVel -= 3.4 * Math.sqrt(impact);

          // толчок в сторону от точки удара
          const mid = (surface.left + surface.right) / 2;
          this.shearVel += (this.x - mid) * -0.03 + (Math.random() - 0.5) * 0.5;

          this.vy = 0;
          this.y = surface.y - (this.h / 2) * this.sy;
        }
      }
    }

    // на земле низ всегда лежит на поверхности
    if (this.onGround && surface) {
      this.y = surface.y - (this.h / 2) * this.sy;
    }

    this.draw();
  }

  draw() {
    const g = this.graphics;
    const n = 64;
    const sx = this.sx;
    const sy = this.sy;

    g.clear();

    g.fillStyle(this.color, 0.97);
    g.beginPath();

    for (let i = 0; i < n; i++) {
      const p = JellyBody.stadiumPoint(i / n, this.w, this.h);
      const shear = this.shear * (0.5 - p.y / this.h);
      const px = this.x + p.x * sx + shear;
      const py = this.y + p.y * sy;

      if (i === 0) g.moveTo(px, py);
      else g.lineTo(px, py);
    }

    g.closePath();
    g.fillPath();

    // мягкий блик
    g.fillStyle(0xffffff, 0.2);
    g.fillEllipse(
      this.x - this.w * 0.12 * sx + this.shear * 0.5,
      this.y - this.h * 0.16 * sy,
      this.w * 0.3 * sx,
      this.h * 0.22 * sy
    );
  }

  destroy() {
    this.graphics.destroy();
  }
}
