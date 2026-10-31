"""
Meat netting applicator (Browin 310090 style) for Fusion 360.

Creates a new design with two bodies:
  1. Applicator  - tube + rounded square flange. Netting is bunched on the
                   OUTSIDE of the tube; the meat is pushed through the bore from
                   the flange side and the netting pulls off the exit lip onto it.
  2. Bracket     - L-bracket that bolts to the flange's bottom edge and clamps or
                   screws to a table top, holding the tube horizontal past the edge.

Coordinates: Z is the tube axis, Z=0 is the back face of the flange,
the tube points toward +Z. All dimensions below are in millimetres.
Edit the values, then re-run the script (it makes a fresh document each time).
"""

import adsk.core
import adsk.fusion
import traceback

# ---------------- Parameters (mm) ----------------
BORE_D = 100.0     # inside diameter the meat passes through
WALL = 3.0         # tube wall thickness
TUBE_LEN = 150.0   # tube length in front of the flange (holds the bunched netting)
LEAD_IN = 5.0      # radial size of the entry funnel at the back of the bore
TIP_LEN = 8.0      # length of the outer taper at the exit lip
TIP_IN = 1.5       # how much the wall thins at the exit lip (net slides off cleanly)

FLANGE = 172.0     # square flange size
FLANGE_T = 6.0     # flange thickness
FLANGE_R = 15.0    # flange corner radius
COLLAR = 8.0       # extra hub radius where the tube meets the flange
GUSSET = 4.0       # 45 deg fillet ring between tube and flange

CORNER_HOLE_D = 5.5  # 4 holes for screwing the flange flat (vertical use)
BOLT_D = 5.5         # 2 holes joining flange and bracket (M5 bolts + nuts)
BOLT_X = 30.0        # bolt offset from centre line

BRACKET_W = 90.0   # bracket width (X)
BRACKET_T = 6.0    # bracket plate thickness
LEG_H = 24.0       # height of the leg that bolts to the flange (keep below the bore)
TAB_LEN = 60.0     # length of the foot that sits on the table
RIB_T = 6.0        # stiffening ribs
RIB_L = 30.0
TABLE_HOLE_D = 5.0 # screw holes in the foot (or just use a C-clamp)
# --------------------------------------------------


def mm(v):
    return v / 10.0  # Fusion API works in cm


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        sketches = root.sketches
        extrudes = root.features.extrudeFeatures
        VI = adsk.core.ValueInput
        Op = adsk.fusion.FeatureOperations

        def sp(sk, x, y, z):
            # model mm -> sketch space, so every plane's axis quirks are handled
            return sk.modelToSketchSpace(adsk.core.Point3D.create(mm(x), mm(y), mm(z)))

        def poly(sk, pts):
            lines = sk.sketchCurves.sketchLines
            first = lines.addByTwoPoints(sp(sk, *pts[0]), sp(sk, *pts[1]))
            prev = first
            for p in pts[2:]:
                prev = lines.addByTwoPoints(prev.endSketchPoint, sp(sk, *p))
            lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)

        def extrude(prof, dist, op, symmetric=False, bodies=None):
            inp = extrudes.createInput(prof, op)
            if symmetric:
                inp.setSymmetricExtent(VI.createByReal(mm(dist)), True)
            else:
                inp.setDistanceExtent(False, VI.createByReal(mm(dist)))
            if bodies:
                inp.participantBodies = bodies
            return extrudes.add(inp)

        def cut_through(profs, bodies=None):
            inp = extrudes.createInput(profs, Op.CutFeatureOperation)
            inp.setAllExtent(adsk.fusion.ExtentDirections.SymmetricExtentDirection)
            if bodies:
                inp.participantBodies = bodies
            return extrudes.add(inp)

        Ri = BORE_D / 2
        Ro = Ri + WALL
        Rc = Ro + COLLAR
        T = FLANGE_T + TUBE_LEN
        h = FLANGE / 2

        # 1. Tube: revolve a half cross-section (r, z) around Z
        sk = sketches.add(root.xZConstructionPlane)
        sk.name = 'Tube profile'
        tube_pts = [
            (Ri + LEAD_IN, 0), (Rc, 0), (Rc, FLANGE_T),
            (Ro + GUSSET, FLANGE_T), (Ro, FLANGE_T + GUSSET),
            (Ro, T - TIP_LEN), (Ro - TIP_IN, T),
            (Ri, T), (Ri, FLANGE_T),
        ]
        poly(sk, [(r, 0, z) for r, z in tube_pts])
        axis = sk.sketchCurves.sketchLines.addByTwoPoints(sp(sk, 0, 0, 0), sp(sk, 0, 0, T))
        axis.isConstruction = True
        revolves = root.features.revolveFeatures
        rin = revolves.createInput(sk.profiles.item(0), axis, Op.NewBodyFeatureOperation)
        rin.setAngleExtent(False, VI.createByString('360 deg'))
        applicator = revolves.add(rin).bodies.item(0)
        applicator.name = 'Applicator'

        # 2. Rounded square flange with the bore opening
        sk = sketches.add(root.xYConstructionPlane)
        sk.name = 'Flange'
        lines = sk.sketchCurves.sketchLines
        arcs = sk.sketchCurves.sketchArcs
        a, b = h - FLANGE_R, h
        sides = [((-a, -b), (a, -b), (a, -a)),   # bottom, then corner centre
                 ((b, -a), (b, a), (a, a)),      # right
                 ((a, b), (-a, b), (-a, a)),     # top
                 ((-b, a), (-b, -a), (-a, -a))]  # left
        for s, e, c in sides:
            ln = lines.addByTwoPoints(sp(sk, s[0], s[1], 0), sp(sk, e[0], e[1], 0))
            arcs.addByCenterStartSweep(sp(sk, c[0], c[1], 0), ln.endSketchPoint, 3.14159265358979 / 2)
        sk.sketchCurves.sketchCircles.addByCenterRadius(sp(sk, 0, 0, 0), mm(Ri + LEAD_IN))
        prof = [p for p in sk.profiles if p.profileLoops.count == 2][0]
        extrude(prof, FLANGE_T, Op.JoinFeatureOperation, bodies=[applicator])

        # 3. Bracket: L-profile in the YZ plane, extruded symmetric in X
        sk = sketches.add(root.yZConstructionPlane)
        sk.name = 'Bracket profile'
        poly(sk, [(0, -h, 0), (0, -h + LEG_H, 0), (0, -h + LEG_H, -BRACKET_T),
                  (0, -h + BRACKET_T, -BRACKET_T), (0, -h + BRACKET_T, -TAB_LEN),
                  (0, -h, -TAB_LEN)])
        bracket = extrude(sk.profiles.item(0), BRACKET_W, Op.NewBodyFeatureOperation,
                          symmetric=True).bodies.item(0)
        bracket.name = 'Bracket'

        # 4. Ribs at both edges of the bracket
        planes = root.constructionPlanes
        for side in (-1, 1):
            pin = planes.createInput()
            pin.setByOffset(root.yZConstructionPlane,
                            VI.createByReal(mm(side * (BRACKET_W / 2 - RIB_T / 2))))
            plane = planes.add(pin)
            sk = sketches.add(plane)
            sk.name = 'Rib'
            x = side * (BRACKET_W / 2 - RIB_T / 2)
            poly(sk, [(x, -h + BRACKET_T, -BRACKET_T), (x, -h + LEG_H, -BRACKET_T),
                      (x, -h + BRACKET_T, -BRACKET_T - RIB_L)])
            extrude(sk.profiles.item(0), RIB_T, Op.JoinFeatureOperation,
                    symmetric=True, bodies=[bracket])

        # 5. Holes along Z: bracket bolts (through flange + leg) and flange corner holes
        sk = sketches.add(root.xYConstructionPlane)
        sk.name = 'Flange holes'
        circles = sk.sketchCurves.sketchCircles
        for x in (-BOLT_X, BOLT_X):
            circles.addByCenterRadius(sp(sk, x, -h + LEG_H / 2, 0), mm(BOLT_D / 2))
        for x in (-a, a):
            for y in (-a, a):
                circles.addByCenterRadius(sp(sk, x, y, 0), mm(CORNER_HOLE_D / 2))
        profs = adsk.core.ObjectCollection.create()
        for p in sk.profiles:
            profs.add(p)
        cut_through(profs, bodies=[applicator, bracket])

        # 6. Holes along Y through the bracket foot, for table screws
        sk = sketches.add(root.xZConstructionPlane)
        sk.name = 'Table holes'
        for x in (-BRACKET_W / 4, BRACKET_W / 4):
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                sp(sk, x, 0, -TAB_LEN + 12), mm(TABLE_HOLE_D / 2))
        profs = adsk.core.ObjectCollection.create()
        for p in sk.profiles:
            profs.add(p)
        cut_through(profs, bodies=[bracket])

        app.activeViewport.fit()

    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
