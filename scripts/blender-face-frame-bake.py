"""Offline Scale Master transfer into the canonical face UV frame used by the current consumer.
Usage: blender -b --python-exit-code 1 --python SCRIPT -- CANONICAL REFERENCE AUDIT SURFACE_MAP OUTPUT SOURCE_FRAME_CHECK
No GLB export; geometry/runtime UVs are unchanged. The shared UV0 establishes correspondence
between reference and canonical corners. The destination is art_uv_set where configured.
Direct side-top copy requires a previously verified full canonical source-frame check.
"""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils.kdtree import KDTree
canonical_path,reference_path,audit_path,registry_path,output,correspondence_path=map(Path,sys.argv[sys.argv.index('--')+1:])
faces={'seat':'ASSENTO','backrest-front':'ENCOSTO_FRONTAL','backrest-side':'ENCOSTO_LATERAL','backrest-rear':'ENCOSTO_TRASEIRO','side-outer':'LATERAL_EXTERNA','side-inner':'LATERAL_INTERNA','side-rear':'LATERAL_REAR','side-top':'LATERAL_TOP'}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def load(p,prefix):
 before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(p));out={}
 for o in set(bpy.data.objects)-before:
  if o.name in faces.values():out[o.name]=o
  o.name=prefix+o.name;o.hide_render=True
 return out
canonical=load(canonical_path,'CANON::')
reference=load(reference_path,'REF::')
registry=json.load(open(registry_path))
uvs={s['surface_id']:s.get('texture_frame',{}).get('art_uv_set',0) for s in registry['surfaces']}
audit=json.load(open(audit_path))
report={};output.mkdir(parents=True,exist_ok=True)
if hashlib.sha256(reference_path.read_bytes()).hexdigest()!=audit['reference_glb']['sha256']:raise RuntimeError('Reference hash differs from audit')
if hashlib.sha256(canonical_path.read_bytes()).hexdigest()!=registry['geometry']['sha256']:raise RuntimeError('Canonical hash differs from registry')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=16
for face,name in faces.items():
 c=canonical[name];r=reference[name];source_uv=audit['faces'][face]['source_uv_set'];target_uv=uvs[face]
 if face=='side-top':
  check=json.load(open(correspondence_path))[name]
  if check['unmatched']!=0:raise RuntimeError('side-top direct UV correspondence failed')
  import shutil
  shutil.copyfile(reference_path.parent/'LATERAL_TOP.webp',output/'side-top.webp')
  report[face]={'source_uv_set':source_uv,'target_uv_set':target_uv,'method':'verified-direct-source-copy','max_uv_error':check['max_source_frame_uv_error'],'status':'PASS'}
  continue
 vals=[(c.matrix_world@c.data.vertices[l.vertex_index].co,c.data.uv_layers[0].data[l.index].uv.copy(),c.data.uv_layers[target_uv].data[l.index].uv.copy()) for l in c.data.loops]
 kd=KDTree(len(vals))
 for i,(p,u,v) in enumerate(vals):kd.insert(p,i)
 kd.balance();target=r.data.uv_layers.new(name='CANONICAL_FACE_TARGET');maxspread=0
 for l in r.data.loops:
  pos=r.matrix_world@r.data.vertices[l.vertex_index].co;uv0=r.data.uv_layers[0].data[l.index].uv;candidates=[]
  for point in (pos,(pos.x,-pos.y,pos.z)):
   for co,i,d in kd.find_range(point,0.0002):
    err=max(abs(uv0[k]-vals[i][1][k]) for k in (0,1))
    if err<0.0005:candidates.append((err,d,i))
  if not candidates:raise RuntimeError(face+' unmatched canonical corner')
  min_error=min(x[0] for x in candidates);candidates=[x for x in candidates if x[0]<=min_error+1e-7]
  best=min(candidates)[2];uv=vals[best][2]
  spread=max(max(abs(uv[k]-vals[x[2]][2][k]) for k in (0,1)) for x in candidates)
  if spread>0.0005:raise RuntimeError(face+' ambiguous target UV '+str(spread))
  maxspread=max(maxspread,spread);target.data[l.index].uv=uv
 original=r.data.materials[0];images=[n.image for n in original.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
 if len(images)!=1:raise RuntimeError('ambiguous image '+face)
 image=images[0];w,h=image.size;dest=bpy.data.images.new(face,width=w,height=h,alpha=True);dest.colorspace_settings.name='sRGB'
 mat=bpy.data.materials.new(face);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
 tex=nodes.new('ShaderNodeTexImage');tex.image=image;uv=nodes.new('ShaderNodeUVMap');uv.uv_map=r.data.uv_layers[source_uv].name;em=nodes.new('ShaderNodeEmission');out=nodes.new('ShaderNodeOutputMaterial');links.new(uv.outputs[0],tex.inputs['Vector']);links.new(tex.outputs['Color'],em.inputs['Color']);links.new(em.outputs[0],out.inputs[0]);t=nodes.new('ShaderNodeTexImage');t.image=dest;nodes.active=t
 r.data.materials.clear();r.data.materials.append(mat);r.data.uv_layers.active_index=len(r.data.uv_layers)-1;target.active_render=True
 bpy.ops.object.select_all(action='DESELECT');r.hide_render=False;r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.bake(type='EMIT')
 dest.filepath_raw=str(output/(face+'.png'));dest.file_format='PNG';dest.save();r.hide_render=True
 report[face]={'source_uv_set':source_uv,'target_uv_set':target_uv,'reference_corners':len(r.data.loops),'max_target_uv_ambiguity':maxspread,'status':'PASS'};print('BAKED',face,flush=True)
(output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
