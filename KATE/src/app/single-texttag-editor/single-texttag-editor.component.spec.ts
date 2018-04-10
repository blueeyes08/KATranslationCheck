import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SingleTexttagEditorComponent } from './single-texttag-editor.component';

describe('SingleTexttagEditorComponent', () => {
  let component: SingleTexttagEditorComponent;
  let fixture: ComponentFixture<SingleTexttagEditorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SingleTexttagEditorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SingleTexttagEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
